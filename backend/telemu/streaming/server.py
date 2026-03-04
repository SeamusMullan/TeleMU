"""Telemetry streaming server (driver side).

Broadcasts live telemetry to LAN clients via the TMU v2 protocol:
- UDP broadcast discovery on the discovery port (default 19740, every 2 seconds)
- TCP control channel on the control port (default 19742) for handshake and
  channel negotiation
- UDP unicast telemetry frames on the telemetry port (default 19741) to each
  subscribed client

Runs as asyncio tasks alongside TelemetryReader.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Protocol constants ────────────────────────────────────────────────────────

MAGIC = b"TMU\x02"
PROTOCOL_VERSION = 1

# Message types
MSG_DISCOVERY_ANNOUNCE = 0x01
MSG_HELLO = 0x10
MSG_WELCOME = 0x11
MSG_SUBSCRIBE = 0x12
MSG_SUBSCRIBED = 0x13
MSG_SESSION_UPDATE = 0x14
MSG_PING = 0x15
MSG_PONG = 0x16
MSG_DISCONNECT = 0x1F

# Disconnect reasons
REASON_NORMAL = 0x00
REASON_VERSION_MISMATCH = 0x01
REASON_SESSION_END = 0x02

# ── Channel registry ──────────────────────────────────────────────────────────
# (id, name, unit, type, min, max) — type: 0=float64

CHANNEL_DEFS: list[tuple[int, str, str, int, float, float]] = [
    (0,  "speed",         "km/h", 0,    0.0,   400.0),
    (1,  "rpm",           "rpm",  0,    0.0, 16000.0),
    (2,  "throttle",      "%",    0,    0.0,   100.0),
    (3,  "brake",         "%",    0,    0.0,   100.0),
    (4,  "gear",          "",     0,   -1.0,     8.0),
    (5,  "steering",      "deg",  0, -900.0,   900.0),
    (6,  "fuel",          "L",    0,    0.0,   200.0),
    (7,  "fuel_capacity", "L",    0,    0.0,   200.0),
    (8,  "rpm_max",       "rpm",  0,    0.0, 16000.0),
    (9,  "tyre_fl",       "C",    0,    0.0,   200.0),
    (10, "tyre_fr",       "C",    0,    0.0,   200.0),
    (11, "tyre_rl",       "C",    0,    0.0,   200.0),
    (12, "tyre_rr",       "C",    0,    0.0,   200.0),
    (13, "brake_temp",    "C",    0,    0.0,  1200.0),
]

_ALL_CHANNELS_MASK: int = (1 << len(CHANNEL_DEFS)) - 1


# ── Helpers ───────────────────────────────────────────────────────────────────


def _pack_str(s: str, size: int) -> bytes:
    """Encode *s* as UTF-8, truncate/null-pad to exactly *size* bytes."""
    return s.encode("utf-8")[:size].ljust(size, b"\x00")


# ── Wire builders (exported for tests) ───────────────────────────────────────


def build_discovery_packet(
    driver_name: str,
    track_name: str,
    vehicle_name: str,
    session_type: int,
    tcp_port: int,
    udp_port: int,
    session_id: int,
) -> bytes:
    """Build a 176-byte DISCOVERY_ANNOUNCE UDP broadcast packet."""
    return struct.pack(
        "<4sHB32s64s64sBHHI",
        MAGIC,
        PROTOCOL_VERSION,
        MSG_DISCOVERY_ANNOUNCE,
        _pack_str(driver_name, 32),
        _pack_str(track_name, 64),
        _pack_str(vehicle_name, 64),
        session_type & 0xFF,
        tcp_port & 0xFFFF,
        udp_port & 0xFFFF,
        session_id & 0xFFFFFFFF,
    )


def build_welcome_message(session_id: int) -> bytes:
    """Build a WELCOME TCP control message with the full channel list."""
    channel_list = bytearray()
    for cid, name, unit, ch_type, min_val, max_val in CHANNEL_DEFS:
        channel_list += struct.pack(
            "<H32s16sBdd",
            cid,
            _pack_str(name, 32),
            _pack_str(unit, 16),
            ch_type,
            min_val,
            max_val,
        )
    payload = struct.pack("<IH", session_id, len(CHANNEL_DEFS)) + bytes(channel_list)
    return struct.pack("<4sHB", MAGIC, len(payload), MSG_WELCOME) + payload


def build_subscribed_message(channel_mask: int) -> bytes:
    """Build a SUBSCRIBED TCP control message."""
    num_bytes = (len(CHANNEL_DEFS) + 7) // 8
    mask_bytes = channel_mask.to_bytes(num_bytes, "little")
    return struct.pack("<4sHB", MAGIC, len(mask_bytes), MSG_SUBSCRIBED) + mask_bytes


def build_disconnect_message(reason: int = REASON_NORMAL) -> bytes:
    """Build a DISCONNECT TCP control message."""
    payload = struct.pack("<B", reason)
    return struct.pack("<4sHB", MAGIC, len(payload), MSG_DISCONNECT) + payload


def build_pong_message(echo_ts: float) -> bytes:
    """Build a PONG TCP control message."""
    payload = struct.pack("<d", echo_ts)
    return struct.pack("<4sHB", MAGIC, len(payload), MSG_PONG) + payload


def build_session_update_message(track: str, vehicle: str, session_type: int) -> bytes:
    """Build a SESSION_UPDATE TCP control message."""
    payload = struct.pack(
        "<64s64sB",
        _pack_str(track, 64),
        _pack_str(vehicle, 64),
        session_type & 0xFF,
    )
    return struct.pack("<4sHB", MAGIC, len(payload), MSG_SESSION_UPDATE) + payload


def build_telemetry_frame(
    session_id: int,
    sequence: int,
    timestamp: float,
    channels: dict[str, float],
    channel_mask: int,
) -> bytes:
    """Build a UDP telemetry frame packet."""
    channel_data = bytearray()
    count = 0
    for cid, name, *_ in CHANNEL_DEFS:
        if (channel_mask >> cid) & 1 and name in channels:
            channel_data += struct.pack("<Hd", cid, float(channels[name]))
            count += 1
    header = struct.pack(
        "<4sIIdH",
        MAGIC,
        session_id & 0xFFFFFFFF,
        sequence & 0xFFFFFFFF,
        timestamp,
        count,
    )
    return header + bytes(channel_data)


# ── Per-client state ──────────────────────────────────────────────────────────


@dataclass
class _ClientState:
    """State for one connected TCP client."""

    addr: str
    telemetry_port: int
    channel_mask: int = field(default_factory=lambda: _ALL_CHANNELS_MASK)
    writer: asyncio.StreamWriter | None = None


# ── TelemetryStreamer ─────────────────────────────────────────────────────────


class TelemetryStreamer:
    """Streams live telemetry to LAN clients via UDP/TCP.

    Usage::

        streamer = TelemetryStreamer()
        reader.subscribe(streamer.on_frame)   # wire into TelemetryReader
        await streamer.start()
        ...
        await streamer.stop()
    """

    def __init__(
        self,
        host: str = "",
        discovery_port: int = 19740,
        telemetry_port: int = 19741,
        control_port: int = 19742,
        driver_name: str = "",
    ) -> None:
        self._host = host
        self._discovery_port = discovery_port
        self._telemetry_port = telemetry_port
        self._control_port = control_port
        self._driver_name = driver_name or socket.gethostname()

        self._running = False
        self._session_id: int = int(time.time()) & 0xFFFFFFFF
        self._sequence: int = 0

        self._clients: dict[str, _ClientState] = {}
        self._tasks: list[asyncio.Task] = []
        self._tcp_server: asyncio.Server | None = None
        self._udp_sock: socket.socket | None = None

        self._track_name: str = ""
        self._vehicle_name: str = ""

        # Rolling throughput metrics
        self._bytes_sent: int = 0
        self._rate_window_start: float = time.monotonic()
        self._data_rate_bps: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    @property
    def clients_connected(self) -> int:
        return len(self._clients)

    @property
    def data_rate_bps(self) -> float:
        return self._data_rate_bps

    @property
    def host(self) -> str:
        return self._host

    @property
    def discovery_port(self) -> int:
        return self._discovery_port

    @property
    def telemetry_port(self) -> int:
        return self._telemetry_port

    @property
    def control_port(self) -> int:
        return self._control_port

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._session_id = int(time.time()) & 0xFFFFFFFF
        self._sequence = 0

        # UDP socket for discovery broadcasts and telemetry unicast
        self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._udp_sock.setblocking(False)

        bind_host = self._host or "0.0.0.0"

        # TCP control server
        self._tcp_server = await asyncio.start_server(
            self._handle_tcp_client,
            host=bind_host,
            port=self._control_port,
        )
        self._tasks.append(asyncio.create_task(self._tcp_server.serve_forever()))
        self._tasks.append(asyncio.create_task(self._discovery_loop()))

        logger.info(
            "TelemetryStreamer started — discovery=%d, telemetry=%d, control=%d",
            self._discovery_port,
            self._telemetry_port,
            self._control_port,
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False

        # Gracefully disconnect all clients
        for client in list(self._clients.values()):
            if client.writer:
                try:
                    client.writer.write(build_disconnect_message(REASON_SESSION_END))
                    await client.writer.drain()
                    client.writer.close()
                except Exception:
                    pass
        self._clients.clear()

        if self._tcp_server:
            self._tcp_server.close()
            await self._tcp_server.wait_closed()
            self._tcp_server = None

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._tasks.clear()

        if self._udp_sock:
            self._udp_sock.close()
            self._udp_sock = None

        logger.info("TelemetryStreamer stopped")

    def on_frame(self, frame: Any) -> None:
        """Sync callback for TelemetryReader — schedules UDP broadcast."""
        if not self._running or not self._clients:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_frame(frame))
        except RuntimeError:
            pass

    # ── Internal: Discovery ───────────────────────────────────────────────────

    async def _discovery_loop(self) -> None:
        """Broadcast DISCOVERY_ANNOUNCE every 2 seconds."""
        try:
            while self._running:
                packet = build_discovery_packet(
                    driver_name=self._driver_name,
                    track_name=self._track_name,
                    vehicle_name=self._vehicle_name,
                    session_type=0,
                    tcp_port=self._control_port,
                    udp_port=self._telemetry_port,
                    session_id=self._session_id,
                )
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: self._udp_sock.sendto(
                            packet, ("<broadcast>", self._discovery_port)
                        ),
                    )
                except Exception as exc:
                    logger.debug("Discovery broadcast error: %s", exc)
                await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            pass

    # ── Internal: TCP control ─────────────────────────────────────────────────

    async def _handle_tcp_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle one TCP control connection (handshake + keep-alive)."""
        addr = writer.get_extra_info("peername")
        client_ip = addr[0] if addr else "unknown"
        logger.info("Control connection from %s", client_ip)

        client = _ClientState(
            addr=client_ip,
            telemetry_port=self._telemetry_port,
            writer=writer,
        )

        try:
            # ── HELLO ────────────────────────────────────────────────────────
            try:
                header = await asyncio.wait_for(reader.readexactly(7), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for HELLO from %s", client_ip)
                return

            magic, length, msg_type = struct.unpack("<4sHB", header)
            if magic != MAGIC:
                logger.warning("Bad magic from %s", client_ip)
                return
            if msg_type != MSG_HELLO:
                logger.warning("Expected HELLO from %s, got 0x%02x", client_ip, msg_type)
                return

            payload = await reader.readexactly(length) if length else b""
            if len(payload) >= 34:
                client_name = payload[:32].rstrip(b"\x00").decode("utf-8", errors="replace")
                proto_ver = struct.unpack_from("<H", payload, 32)[0]
                logger.debug(
                    "HELLO from %s: name=%s ver=%d", client_ip, client_name, proto_ver
                )

            # ── WELCOME ───────────────────────────────────────────────────────
            writer.write(build_welcome_message(self._session_id))
            await writer.drain()

            # ── SUBSCRIBE ─────────────────────────────────────────────────────
            try:
                header = await asyncio.wait_for(reader.readexactly(7), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for SUBSCRIBE from %s", client_ip)
                return

            magic, length, msg_type = struct.unpack("<4sHB", header)
            if magic == MAGIC and msg_type == MSG_SUBSCRIBE and length > 0:
                mask_bytes = await reader.readexactly(length)
                channel_mask = int.from_bytes(mask_bytes, "little") & _ALL_CHANNELS_MASK
                client.channel_mask = channel_mask if channel_mask else _ALL_CHANNELS_MASK
            elif length > 0:
                await reader.readexactly(length)

            # ── SUBSCRIBED ────────────────────────────────────────────────────
            writer.write(build_subscribed_message(client.channel_mask))
            await writer.drain()

            # Register client — UDP frames will now be sent to this address
            self._clients[client_ip] = client
            logger.info(
                "Client %s subscribed (mask=0x%x, total=%d)",
                client_ip,
                client.channel_mask,
                len(self._clients),
            )

            # ── Keep-alive: handle PING / DISCONNECT ──────────────────────────
            while self._running:
                try:
                    header_data = await asyncio.wait_for(
                        reader.readexactly(7), timeout=30.0
                    )
                except asyncio.TimeoutError:
                    continue
                except asyncio.IncompleteReadError:
                    break

                magic, length, msg_type = struct.unpack("<4sHB", header_data)
                if magic != MAGIC:
                    break

                data = await reader.readexactly(length) if length else b""

                if msg_type == MSG_PING:
                    ts = struct.unpack_from("<d", data)[0] if len(data) >= 8 else 0.0
                    writer.write(build_pong_message(ts))
                    await writer.drain()
                elif msg_type == MSG_DISCONNECT:
                    logger.info("Client %s disconnected gracefully", client_ip)
                    break

        except asyncio.IncompleteReadError:
            logger.debug("Client %s disconnected (incomplete read)", client_ip)
        except Exception:
            logger.exception("Error handling client %s", client_ip)
        finally:
            self._clients.pop(client_ip, None)
            try:
                writer.close()
            except Exception:
                pass
            logger.info("Client %s removed (%d remaining)", client_ip, len(self._clients))

    # ── Internal: Telemetry broadcast ─────────────────────────────────────────

    async def _broadcast_frame(self, frame: Any) -> None:
        """Send one telemetry frame to all subscribed clients via UDP unicast."""
        if not self._clients or not self._udp_sock:
            return

        self._sequence = (self._sequence + 1) & 0xFFFFFFFF
        total_bytes = 0
        loop = asyncio.get_running_loop()

        for client in list(self._clients.values()):
            packet = build_telemetry_frame(
                session_id=self._session_id,
                sequence=self._sequence,
                timestamp=frame.ts,
                channels=frame.channels,
                channel_mask=client.channel_mask,
            )
            dest = (client.addr, client.telemetry_port)
            try:
                await loop.run_in_executor(
                    None,
                    lambda p=packet, d=dest: self._udp_sock.sendto(p, d),
                )
                total_bytes += len(packet)
            except Exception as exc:
                logger.debug("UDP send to %s failed: %s", client.addr, exc)

        self._bytes_sent += total_bytes
        self._update_rate()

    def _update_rate(self) -> None:
        """Recompute rolling data rate (bytes/s) once per second."""
        now = time.monotonic()
        elapsed = now - self._rate_window_start
        if elapsed >= 1.0:
            self._data_rate_bps = self._bytes_sent / elapsed
            self._bytes_sent = 0
            self._rate_window_start = now
