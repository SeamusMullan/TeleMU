"""StreamClient — engineer-side streaming client.

Responsibilities
----------------
* Listens for DISCOVERY_ANNOUNCE broadcasts on UDP :9099.
* Connects via TCP to the driver's control port for handshake.
* Receives UDP telemetry frames on a dedicated local port.
* Emits decoded :class:`~telemu.streaming.protocol.TelemetryFrame` objects
  via a callback.

Thread model
------------
``StreamClient`` owns two background threads once connected:
- *control thread*: reads control messages from the TCP socket.
- *telemetry thread*: receives and decodes UDP telemetry frames.

Usage
-----
::

    def on_frame(frame):
        print(frame.timestamp, frame.channels)

    client = StreamClient(on_frame=on_frame)
    drivers = client.discover(timeout=3.0)
    if drivers:
        client.connect(drivers[0]["ip"], drivers[0]["tcp_port"])
    # ...later:
    client.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from collections import deque

from telemu.streaming.protocol import (
    CTRL_HDR,
    CTRL_HDR_SIZE,
    DEFAULT_TCP_PORT,
    DEFAULT_UDP_PORT,
    HEARTBEAT_TIMEOUT,
    MAGIC,
    MSG_DISCONNECT,
    MSG_PING,
    MSG_PONG,
    MSG_SESSION_UPDATE,
    MSG_SUBSCRIBED,
    MSG_WELCOME,
    PING_FMT,
    WELCOME_BASE_FMT,
    CHANNEL_ENTRY_FMT,
    CHANNEL_ENTRY_SIZE,
    parse_udp_frame,
    pack_hello,
    pack_pong,
    pack_subscribe,
)
from telemu.ws import protocol as ws_protocol
from telemu.ws.manager import ConnectionManager

logger = logging.getLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────────

BUFFER_MS: float = 100.0           # jitter-buffer window in milliseconds
RECONNECT_BASE_DELAY: float = 1.0  # initial reconnect delay (seconds)
RECONNECT_MAX_DELAY: float = 30.0  # maximum reconnect delay (seconds)
CONNECT_TIMEOUT: float = 5.0       # TCP connect + handshake timeout

# ── State constants ───────────────────────────────────────────────────────────

STATE_IDLE = "idle"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_RECONNECTING = "reconnecting"


# ── Internal UDP protocol handler ─────────────────────────────────────────────


class _UDPProtocol(asyncio.DatagramProtocol):
    """Minimal asyncio UDP handler that delegates each datagram to *callback*."""

    def __init__(self, callback) -> None:
        self._callback = callback

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        self._callback(data)

    def error_received(self, exc: Exception) -> None:
        logger.debug("UDP error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        pass


# ── Channel map ───────────────────────────────────────────────────────────────


def _parse_channel_list(data: bytes) -> dict[int, str]:
    """Parse the WELCOME channel list payload.

    Returns a mapping of ``channel_id → channel_name``.
    """
    channels: dict[int, str] = {}
    offset = 0
    while offset + CHANNEL_ENTRY_SIZE <= len(data):
        ch_id, name_b, _unit_b, _ch_type, _min_val, _max_val = (
            CHANNEL_ENTRY_FMT.unpack(data[offset : offset + CHANNEL_ENTRY_SIZE])
        )
        name = name_b.rstrip(b"\x00").decode(errors="replace")
        channels[ch_id] = name
        offset += CHANNEL_ENTRY_SIZE
    return channels


# ── Public class ──────────────────────────────────────────────────────────────


class StreamingClient:
    """Engineer-side telemetry streaming client.

    Usage::

        client = StreamingClient(ws_manager)
        await client.start("192.168.1.10", 9101)
        ...
        await client.stop()

    The client feeds received telemetry frames directly into *ws_manager*
    broadcasts so that the existing :class:`~telemu.ws.manager.ConnectionManager`
    distributes frames to all connected WebSocket clients.
    """

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

        # Configuration
        self._host: str = ""
        self._port: int = DEFAULT_TCP_PORT
        self._udp_port: int = DEFAULT_UDP_PORT

        # Runtime
        self._task: asyncio.Task | None = None
        self._running: bool = False
        self._state: str = STATE_IDLE

        # Channel map from WELCOME: channel_id → name
        self._channel_map: dict[int, str] = {}

        # Statistics
        self._last_seq: int = -1
        self._lost_packets: int = 0
        self._rx_frames: int = 0

        # Jitter buffer: deque of (recv_ts: float, frame_ts: float, channels: dict)
        self._buffer: deque[tuple[float, float, dict]] = deque()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def connected(self) -> bool:
        return self._state == STATE_CONNECTED

    @property
    def channel_names(self) -> list[str]:
        return list(self._channel_map.values())

    @property
    def stats(self) -> dict:
        return {
            "state": self._state,
            "host": self._host,
            "port": self._port,
            "rx_frames": self._rx_frames,
            "lost_packets": self._lost_packets,
            "channel_count": len(self._channel_map),
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, host: str, port: int, udp_port: int = DEFAULT_UDP_PORT) -> None:
        """Start connecting to *host*:*port* in the background."""
        if self._task is not None:
            await self.stop()
        self._host = host
        self._port = port
        self._udp_port = udp_port
        self._running = True
        self._task = asyncio.create_task(
            self._run_with_reconnect(), name="streaming-client"
        )

    async def stop(self) -> None:
        """Stop the client and cancel any background tasks."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._state = STATE_IDLE

    # ── Reconnect loop ────────────────────────────────────────────────────────

    async def _run_with_reconnect(self) -> None:
        delay = RECONNECT_BASE_DELAY
        while self._running:
            self._state = STATE_CONNECTING
            try:
                await self._run_session()
                delay = RECONNECT_BASE_DELAY
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Streaming session ended: %s", exc)

            if not self._running:
                break

            self._state = STATE_RECONNECTING
            logger.info("Reconnecting in %.1f s", delay)
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                raise
            delay = min(delay * 2.0, RECONNECT_MAX_DELAY)

        self._state = STATE_IDLE

    # ── Session ───────────────────────────────────────────────────────────────

    async def _run_session(self) -> None:
        """Run a single connected session (TCP control + UDP data)."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self._host, self._port),
            timeout=CONNECT_TIMEOUT,
        )
        udp_transport: asyncio.BaseTransport | None = None
        try:
            udp_port = await asyncio.wait_for(
                self._handshake(reader, writer), timeout=CONNECT_TIMEOUT
            )

            loop = asyncio.get_running_loop()
            udp_transport, _ = await loop.create_datagram_endpoint(
                lambda: _UDPProtocol(self._on_udp_packet),
                local_addr=("0.0.0.0", udp_port),
            )

            self._state = STATE_CONNECTED
            self._last_seq = -1
            self._rx_frames = 0
            self._lost_packets = 0
            self._buffer.clear()
            logger.info(
                "Streaming connected to %s:%d (UDP :%d)",
                self._host,
                self._port,
                udp_port,
            )

            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._tcp_reader(reader, writer))
                tg.create_task(self._buffer_flusher())

        finally:
            if udp_transport is not None:
                udp_transport.close()
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            self._state = STATE_CONNECTING  # reconnect loop will update this

    # ── TCP handshake ─────────────────────────────────────────────────────────

    async def _handshake(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> int:
        """Perform the TCP handshake and return the UDP port to bind.

        Sequence: HELLO → WELCOME → SUBSCRIBE → SUBSCRIBED
        """
        # Send HELLO
        writer.write(pack_hello())
        await writer.drain()

        # Receive WELCOME
        msg_type, payload = await self._read_ctrl_msg(reader)
        if msg_type != MSG_WELCOME:
            raise ValueError(f"Expected WELCOME (0x{MSG_WELCOME:02x}), got 0x{msg_type:02x}")

        session_id, channel_count = WELCOME_BASE_FMT.unpack(
            payload[: WELCOME_BASE_FMT.size]
        )
        channel_payload = payload[WELCOME_BASE_FMT.size :]
        self._channel_map = _parse_channel_list(channel_payload)
        logger.info(
            "WELCOME: session_id=%d channels=%d", session_id, channel_count
        )

        # Send SUBSCRIBE (all channels)
        writer.write(pack_subscribe(channel_count, subscribe_all=True))
        await writer.drain()

        # Receive SUBSCRIBED
        msg_type, _payload = await self._read_ctrl_msg(reader)
        if msg_type != MSG_SUBSCRIBED:
            raise ValueError(
                f"Expected SUBSCRIBED (0x{MSG_SUBSCRIBED:02x}), got 0x{msg_type:02x}"
            )

        return self._udp_port

    # ── TCP control helpers ───────────────────────────────────────────────────

    @staticmethod
    async def _read_ctrl_msg(
        reader: asyncio.StreamReader,
    ) -> tuple[int, bytes]:
        """Read one TCP control message.

        Returns:
            ``(msg_type, payload)``
        """
        hdr = await reader.readexactly(CTRL_HDR_SIZE)
        magic, length, msg_type = CTRL_HDR.unpack(hdr)
        if magic != MAGIC:
            raise ValueError(f"Bad magic in control message: {magic!r}")
        payload = await reader.readexactly(length) if length else b""
        return msg_type, payload

    # ── TCP reader (heartbeats, session updates) ──────────────────────────────

    async def _tcp_reader(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Read ongoing TCP control messages; raises on heartbeat timeout."""
        while True:
            try:
                msg_type, payload = await asyncio.wait_for(
                    self._read_ctrl_msg(reader), timeout=HEARTBEAT_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise ConnectionError("Heartbeat (PING) timeout")

            if msg_type == MSG_PING:
                ts = PING_FMT.unpack(payload)[0] if len(payload) >= 8 else 0.0
                writer.write(pack_pong(ts))
                await writer.drain()
                logger.debug("PING received, PONG sent")

            elif msg_type == MSG_SESSION_UPDATE:
                logger.debug("SESSION_UPDATE received")

            elif msg_type == MSG_DISCONNECT:
                raise ConnectionError("Server sent DISCONNECT")

            else:
                logger.debug("Unhandled TCP message type 0x%02x", msg_type)

    # ── UDP receiver ──────────────────────────────────────────────────────────

    def _on_udp_packet(self, data: bytes) -> None:
        """Process a received UDP telemetry datagram (called in event loop)."""
        result = parse_udp_frame(data)
        if result is None:
            return

        _session_id, seq, ts, ch_by_id = result
        if not ch_by_id:
            return

        # Resolve channel IDs to names using the map from WELCOME.
        channels: dict[str, float] = {}
        for ch_id, value in ch_by_id.items():
            name = self._channel_map.get(int(ch_id), f"ch{ch_id}")
            channels[name] = value

        # Packet-loss detection (no retransmission; just skip the gap).
        if self._last_seq >= 0:
            expected = (self._last_seq + 1) & 0xFFFFFFFF
            if seq != expected:
                gap = (seq - self._last_seq) & 0xFFFFFFFF
                if gap < 0x80000000:
                    self._lost_packets += gap - 1
        self._last_seq = seq
        self._rx_frames += 1

        # Store the local receive time for the jitter buffer, alongside the
        # original driver timestamp for the broadcast payload.
        self._buffer.append((time.monotonic(), ts, channels))

    # ── Jitter buffer ─────────────────────────────────────────────────────────

    async def _buffer_flusher(self) -> None:
        """Flush frames older than BUFFER_MS from the jitter buffer."""
        interval = BUFFER_MS / 1000.0
        while True:
            await asyncio.sleep(interval)
            cutoff = time.monotonic() - interval
            while self._buffer:
                recv_ts, frame_ts, channels = self._buffer[0]
                if recv_ts <= cutoff:
                    self._buffer.popleft()
                    await self._manager.broadcast(
                        ws_protocol.TELEMETRY,
                        {
                            "type": ws_protocol.TELEMETRY,
                            "ts": frame_ts,
                            "channels": channels,
                        },
                    )
                else:
                    break
