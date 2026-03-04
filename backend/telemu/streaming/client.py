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

import logging
import select
import socket
import struct
import threading
import time
from typing import Callable

from .protocol import (
    CONTROL_PORT,
    DISCOVERY_PORT,
    HEARTBEAT_INTERVAL,
    TELEMETRY_PORT,
    ChannelInfo,
    DisconnectReason,
    MsgType,
    TelemetryFrame,
    _CTRL_HDR_FMT,
    _CTRL_HDR_SIZE,
    STREAM_MAGIC,
    decode_discovery,
    decode_ping_pong,
    decode_session_update,
    decode_welcome,
    decode_subscribed,
    encode_disconnect,
    encode_hello,
    encode_ping,
    encode_pong,
    encode_subscribe,
    decode_telemetry_frame,
)

logger = logging.getLogger(__name__)

_POLL_TIMEOUT = 0.5


class StreamClient:
    """Engineer-side streaming client.

    Parameters
    ----------
    client_name:
        Name sent in the HELLO message (displayed on driver side).
    on_frame:
        Callback invoked with each decoded :class:`TelemetryFrame`.
    on_connected:
        Callback invoked with driver address string when control channel
        is established and stream begins.
    on_disconnected:
        Callback invoked with disconnect reason when the session ends.
    on_session_update:
        Callback invoked with ``{"track", "vehicle", "session_type"}`` dict
        whenever the driver sends SESSION_UPDATE.
    discovery_port, control_port, telemetry_port:
        Override default port numbers (useful for testing).
    """

    def __init__(
        self,
        client_name: str = "Engineer",
        *,
        on_frame: Callable[[TelemetryFrame], None] | None = None,
        on_connected: Callable[[str], None] | None = None,
        on_disconnected: Callable[[int], None] | None = None,
        on_session_update: Callable[[dict], None] | None = None,
        discovery_port: int = DISCOVERY_PORT,
        control_port: int = CONTROL_PORT,
        telemetry_port: int = TELEMETRY_PORT,
    ) -> None:
        self.client_name = client_name

        self._on_frame = on_frame
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._on_session_update = on_session_update

        self._discovery_port = discovery_port
        self._control_port = control_port
        self._telemetry_port = telemetry_port

        self._stop_event = threading.Event()
        self._ctrl_sock: socket.socket | None = None
        self._telem_sock: socket.socket | None = None
        self._threads: list[threading.Thread] = []

        self.session_id: int = 0
        self.channels: list[ChannelInfo] = []
        self._subscribed: list[int] = []

    # ── Discovery ─────────────────────────────────────────────────────────

    def discover(self, timeout: float = 3.0) -> list[dict]:
        """Listen for DISCOVERY_ANNOUNCE broadcasts and return found drivers.

        Parameters
        ----------
        timeout:
            Seconds to listen before returning.

        Returns
        -------
        list[dict]
            Each dict has keys: ``driver_name``, ``track_name``,
            ``vehicle_name``, ``session_type``, ``tcp_port``, ``udp_port``,
            ``session_id``, ``ip``.
        """
        results: list[dict] = []
        seen: set[str] = set()

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("", self._discovery_port))
            sock.settimeout(0.2)

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    data, addr = sock.recvfrom(512)
                    info = decode_discovery(data)
                    key = f"{addr[0]}:{info['tcp_port']}"
                    if key not in seen:
                        seen.add(key)
                        info["ip"] = addr[0]
                        results.append(info)
                except (socket.timeout, ValueError):
                    pass

        return results

    # ── Connection ────────────────────────────────────────────────────────

    def connect(
        self,
        host: str,
        tcp_port: int = CONTROL_PORT,
        subscribe: list[int] | None = None,
        local_udp_port: int = 0,
    ) -> None:
        """Connect to a driver and start receiving telemetry.

        Parameters
        ----------
        host:
            IP address or hostname of the driver's PC.
        tcp_port:
            Driver's TCP control port.
        subscribe:
            List of channel IDs to subscribe to.  An empty list or ``None``
            subscribes to all available channels.
        local_udp_port:
            Local UDP port for telemetry reception (0 = OS-assigned).
        """
        self._stop_event.clear()

        # Open UDP telemetry receive socket first so we have a local port
        self._telem_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._telem_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._telem_sock.bind(("", local_udp_port))
        self._telem_sock.settimeout(_POLL_TIMEOUT)
        actual_udp_port = self._telem_sock.getsockname()[1]

        # TCP control connection
        self._ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._ctrl_sock.settimeout(5.0)
        self._ctrl_sock.connect((host, tcp_port))

        # Handshake
        self._ctrl_sock.sendall(encode_hello(self.client_name))
        welcome_raw = _recv_ctrl_msg(self._ctrl_sock)
        if welcome_raw is None or welcome_raw[0] != MsgType.WELCOME:
            raise ConnectionError("Did not receive WELCOME from driver")
        welcome = decode_welcome(welcome_raw[1])
        self.session_id = welcome["session_id"]
        self.channels = welcome["channels"]

        # Subscribe — include local UDP port so the server knows where to send frames
        channel_ids = subscribe if subscribe is not None else []
        self._ctrl_sock.sendall(encode_subscribe(channel_ids, udp_port=actual_udp_port))
        sub_raw = _recv_ctrl_msg(self._ctrl_sock)
        if sub_raw is None or sub_raw[0] != MsgType.SUBSCRIBED:
            raise ConnectionError("Did not receive SUBSCRIBED confirmation")
        sub_info = decode_subscribed(sub_raw[1])
        self._subscribed = sub_info["channel_ids"]

        logger.info(
            "Connected to driver at %s:%d; session=%d, %d channels",
            host, tcp_port, self.session_id, len(self.channels),
        )

        if self._on_connected:
            self._on_connected(f"{host}:{tcp_port}")

        # Start background threads
        self._ctrl_sock.settimeout(_POLL_TIMEOUT)
        for target, name in (
            (self._ctrl_loop, "client-ctrl"),
            (self._telem_loop, "client-telem"),
            (self._keepalive_loop, "client-keepalive"),
        ):
            t = threading.Thread(target=target, name=name, daemon=True)
            t.start()
            self._threads.append(t)

    def disconnect(self) -> None:
        """Gracefully disconnect from the driver."""
        self._stop_event.set()
        if self._ctrl_sock:
            try:
                self._ctrl_sock.sendall(encode_disconnect(DisconnectReason.CLIENT_REQUEST))
            except OSError:
                pass
        self._cleanup()

    # ── Background threads ────────────────────────────────────────────────

    def _ctrl_loop(self) -> None:
        """Read and dispatch TCP control messages."""
        while not self._stop_event.is_set():
            msg = _recv_ctrl_msg(self._ctrl_sock)
            if msg is False:
                continue  # timeout, no data yet
            if msg is None:
                if not self._stop_event.is_set():
                    logger.warning("Control connection lost")
                    if self._on_disconnected:
                        self._on_disconnected(DisconnectReason.NORMAL)
                    self._stop_event.set()
                break
            self._dispatch_ctrl(*msg)

    def _dispatch_ctrl(self, msg_type: MsgType, payload: bytes) -> None:
        """Handle one incoming control message."""
        if msg_type == MsgType.PING:
            ts = decode_ping_pong(payload)
            try:
                assert self._ctrl_sock is not None
                self._ctrl_sock.sendall(encode_pong(ts))
            except OSError:
                pass
        elif msg_type == MsgType.PONG:
            pass  # latency measurement — ignore for now
        elif msg_type == MsgType.SESSION_UPDATE:
            info = decode_session_update(payload)
            logger.info("Session update: %s", info)
            if self._on_session_update:
                self._on_session_update(info)
        elif msg_type == MsgType.DISCONNECT:
            reason_raw = payload[0] if payload else 0
            logger.info("Driver sent DISCONNECT (reason=%d)", reason_raw)
            if self._on_disconnected:
                self._on_disconnected(reason_raw)
            self._stop_event.set()
        else:
            logger.debug("Unhandled control msg 0x%02X", int(msg_type))

    def _telem_loop(self) -> None:
        """Receive and decode UDP telemetry datagrams."""
        while not self._stop_event.is_set():
            try:
                assert self._telem_sock is not None
                data, _ = self._telem_sock.recvfrom(2048)
                try:
                    frame = decode_telemetry_frame(data)
                    if self._on_frame:
                        self._on_frame(frame)
                except ValueError:
                    logger.debug("Malformed telemetry packet", exc_info=True)
            except socket.timeout:
                pass
            except OSError:
                if not self._stop_event.is_set():
                    logger.debug("Telemetry socket error", exc_info=True)
                break

    def _keepalive_loop(self) -> None:
        """Periodically send PING to the driver."""
        while not self._stop_event.is_set():
            self._stop_event.wait(HEARTBEAT_INTERVAL)
            if self._stop_event.is_set():
                break
            try:
                assert self._ctrl_sock is not None
                self._ctrl_sock.sendall(encode_ping(time.time()))
            except OSError:
                break

    # ── Helpers ───────────────────────────────────────────────────────────

    def _cleanup(self) -> None:
        """Join threads and close sockets."""
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads.clear()
        for s in (self._ctrl_sock, self._telem_sock):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        self._ctrl_sock = None
        self._telem_sock = None


def _recv_ctrl_msg(sock: socket.socket | None) -> tuple[MsgType, bytes] | None | bool:
    """Read one framed control message from *sock*.

    Returns
    -------
    tuple[MsgType, bytes]
        Decoded message on success.
    None
        EOF or hard error (connection closed).
    False
        Timeout — no data yet, caller should retry.
    """
    if sock is None:
        return None
    try:
        header = _recvall(sock, _CTRL_HDR_SIZE)
        if header is False:
            return False  # timeout, no data
        if not header:
            return None   # EOF
        magic, length, msg_type_raw = struct.unpack_from(_CTRL_HDR_FMT, header)
        if magic != STREAM_MAGIC:
            return None
        payload = _recvall(sock, length) if length else b""
        if payload is False or payload is None:
            return None
        return MsgType(msg_type_raw), payload
    except (OSError, ValueError):
        return None


def _recvall(sock: socket.socket, n: int) -> bytes | None | bool:
    """Read exactly *n* bytes from *sock*.

    Returns
    -------
    bytes
        Exactly *n* bytes on success.
    None
        EOF (remote closed connection).
    False
        Timed out before all bytes arrived.
    """
    buf = bytearray()
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout:
            return False
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)
