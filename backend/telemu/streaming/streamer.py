"""TelemetryStreamer — driver-side streaming server.

Responsibilities
----------------
* Broadcasts DISCOVERY_ANNOUNCE on UDP :9099 every 2 seconds.
* Accepts TCP control connections on :9101.
* Manages per-client state: HELLO/WELCOME handshake, SUBSCRIBE/SUBSCRIBED,
  PING/PONG keepalive, DISCONNECT on exit.
* Sends LZ4-compressed telemetry UDP frames to each subscribed client's
  address on :9100.

Thread model
------------
``TelemetryStreamer`` owns three background threads:
- *discovery thread*: periodic UDP broadcast.
- *accept thread*: ``accept()`` loop for TCP control connections.
- *keepalive thread*: sends PING, evicts stale clients.

Frames are pushed from the caller's thread via :meth:`push_frame`.

Usage
-----
::

    streamer = TelemetryStreamer(session_id=42)
    streamer.start()
    # ... in your read loop:
    streamer.push_frame(timestamp=t, channels={0: speed, 1: rpm})
    streamer.stop()
"""

from __future__ import annotations

import logging
import select
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from .protocol import (
    CONTROL_PORT,
    DISCOVERY_PORT,
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT,
    TELEMETRY_PORT,
    ChannelInfo,
    DisconnectReason,
    MsgType,
    SessionType,
    _decode_ctrl_header,
    decode_hello,
    decode_subscribe,
    encode_disconnect,
    encode_discovery,
    encode_ping,
    encode_pong,
    encode_session_update,
    encode_subscribed,
    encode_telemetry_frame,
    encode_welcome,
)

logger = logging.getLogger(__name__)

# How long to wait on sockets before checking stop flag
_POLL_TIMEOUT = 0.5
# Backlog for TCP accept
_TCP_BACKLOG = 8


@dataclass
class _ClientState:
    """Per-client state held by the streamer."""

    address: str          # "ip:port" string
    ip: str
    udp_port: int = TELEMETRY_PORT
    subscribed_channels: set[int] = field(default_factory=set)
    last_pong: float = field(default_factory=time.monotonic)
    sock: socket.socket | None = None  # TCP control socket


class TelemetryStreamer:
    """Driver-side streaming server.

    Parameters
    ----------
    session_id:
        Unique 32-bit integer identifying this session.
    channels:
        Channel metadata list sent to clients during WELCOME.
    driver_name, track_name, vehicle_name, session_type:
        Discovery announcement fields.
    discovery_port, control_port, telemetry_port:
        Override default port numbers (useful for testing).
    on_client_connected, on_client_disconnected:
        Optional callbacks invoked with the client address string.
    """

    def __init__(
        self,
        session_id: int = 0,
        channels: list[ChannelInfo] | None = None,
        driver_name: str = "Driver",
        track_name: str = "",
        vehicle_name: str = "",
        session_type: int = SessionType.UNKNOWN,
        *,
        discovery_port: int = DISCOVERY_PORT,
        control_port: int = CONTROL_PORT,
        telemetry_port: int = TELEMETRY_PORT,
        on_client_connected: Callable[[str], None] | None = None,
        on_client_disconnected: Callable[[str], None] | None = None,
    ) -> None:
        self.session_id = session_id
        self.channels: list[ChannelInfo] = channels or []
        self.driver_name = driver_name
        self.track_name = track_name
        self.vehicle_name = vehicle_name
        self.session_type = session_type

        self._discovery_port = discovery_port
        self._control_port = control_port
        self._telemetry_port = telemetry_port

        self._on_connected = on_client_connected
        self._on_disconnected = on_client_disconnected

        self._stop_event = threading.Event()
        self._clients: dict[str, _ClientState] = {}
        self._clients_lock = threading.Lock()
        self._sequence: int = 0

        self._discovery_sock: socket.socket | None = None
        self._control_sock: socket.socket | None = None
        self._telemetry_sock: socket.socket | None = None

        self._threads: list[threading.Thread] = []

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Open sockets and start background threads."""
        self._stop_event.clear()

        # UDP discovery broadcast socket
        self._discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # TCP control listen socket
        self._control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._control_sock.bind(("", self._control_port))
        self._control_sock.listen(_TCP_BACKLOG)
        self._control_sock.setblocking(False)

        # UDP telemetry send socket (unicast per-client)
        self._telemetry_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for target, name in (
            (self._discovery_loop, "streamer-discovery"),
            (self._accept_loop, "streamer-accept"),
            (self._keepalive_loop, "streamer-keepalive"),
        ):
            t = threading.Thread(target=target, name=name, daemon=True)
            t.start()
            self._threads.append(t)

        logger.info(
            "TelemetryStreamer started (control :%d, telemetry :%d, discovery :%d)",
            self._control_port,
            self._telemetry_port,
            self._discovery_port,
        )

    def stop(self) -> None:
        """Signal background threads to stop and close all sockets."""
        self._stop_event.set()
        self._broadcast_disconnect(DisconnectReason.SERVER_SHUTDOWN)
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads.clear()
        for s in (self._discovery_sock, self._control_sock, self._telemetry_sock):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        with self._clients_lock:
            for client in self._clients.values():
                if client.sock:
                    try:
                        client.sock.close()
                    except OSError:
                        pass
            self._clients.clear()
        logger.info("TelemetryStreamer stopped")

    def push_frame(
        self,
        timestamp: float,
        channels: dict[int, float],
        *,
        compress: bool = True,
    ) -> None:
        """Encode and unicast a telemetry frame to all subscribed clients.

        Parameters
        ----------
        timestamp:
            ``mElapsedTime`` in seconds.
        channels:
            Full channel map; each client's subscription filter is applied
            before sending.
        compress:
            Whether to LZ4-compress the channel payload (default *True*).
        """
        seq = self._sequence
        self._sequence = (seq + 1) & 0xFFFFFFFF

        with self._clients_lock:
            clients = list(self._clients.values())

        for client in clients:
            subset = (
                {k: v for k, v in channels.items() if k in client.subscribed_channels}
                if client.subscribed_channels
                else channels
            )
            if not subset:
                continue
            try:
                packet = encode_telemetry_frame(
                    self.session_id, seq, timestamp, subset, compress=compress
                )
                assert self._telemetry_sock is not None
                self._telemetry_sock.sendto(packet, (client.ip, client.udp_port))
            except (OSError, ValueError):
                logger.debug("Failed to send telemetry to %s", client.address, exc_info=True)

    def connected_clients(self) -> list[str]:
        """Return a list of connected client address strings."""
        with self._clients_lock:
            return list(self._clients.keys())

    def update_session(
        self,
        track: str,
        vehicle: str,
        session_type: int = SessionType.UNKNOWN,
    ) -> None:
        """Broadcast a SESSION_UPDATE to all connected clients."""
        self.track_name = track
        self.vehicle_name = vehicle
        self.session_type = session_type
        msg = encode_session_update(track, vehicle, session_type)
        self._broadcast_ctrl(msg)

    # ── Background threads ────────────────────────────────────────────────

    def _discovery_loop(self) -> None:
        """Broadcast DISCOVERY_ANNOUNCE every 2 seconds."""
        while not self._stop_event.is_set():
            try:
                pkt = encode_discovery(
                    driver_name=self.driver_name,
                    track_name=self.track_name,
                    vehicle_name=self.vehicle_name,
                    session_type=self.session_type,
                    tcp_port=self._control_port,
                    udp_port=self._telemetry_port,
                    session_id=self.session_id,
                )
                assert self._discovery_sock is not None
                self._discovery_sock.sendto(pkt, ("<broadcast>", self._discovery_port))
            except OSError:
                logger.debug("Discovery broadcast failed", exc_info=True)
            self._stop_event.wait(2.0)

    def _accept_loop(self) -> None:
        """Accept incoming TCP control connections."""
        while not self._stop_event.is_set():
            assert self._control_sock is not None
            readable, _, _ = select.select([self._control_sock], [], [], _POLL_TIMEOUT)
            if not readable:
                continue
            try:
                conn, addr = self._control_sock.accept()
                conn.setblocking(True)
                addr_str = f"{addr[0]}:{addr[1]}"
                logger.info("Client connected: %s", addr_str)
                t = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr[0], addr_str),
                    name=f"streamer-client-{addr_str}",
                    daemon=True,
                )
                t.start()
                self._threads.append(t)
            except OSError:
                if not self._stop_event.is_set():
                    logger.debug("Accept error", exc_info=True)

    def _handle_client(self, conn: socket.socket, ip: str, addr_str: str) -> None:
        """Manage handshake and ongoing control messages for one client."""
        state = _ClientState(address=addr_str, ip=ip, sock=conn)
        try:
            # Expect HELLO within 5 seconds
            conn.settimeout(5.0)
            hello_raw = self._recv_ctrl_msg(conn)
            if not hello_raw:
                return
            msg_type, payload = hello_raw
            if msg_type != MsgType.HELLO:
                logger.warning("Expected HELLO from %s, got %s", addr_str, msg_type)
                return
            info = decode_hello(payload)
            logger.info("HELLO from %s (%s, proto v%d)", addr_str, info["client_name"], info["protocol_version"])

            # Send WELCOME
            conn.sendall(encode_welcome(self.session_id, self.channels))

            # Wait for SUBSCRIBE
            conn.settimeout(5.0)
            sub_raw = self._recv_ctrl_msg(conn)
            if not sub_raw:
                return
            msg_type, payload = sub_raw
            if msg_type != MsgType.SUBSCRIBE:
                logger.warning("Expected SUBSCRIBE from %s, got %s", addr_str, msg_type)
                return
            sub_info = decode_subscribe(payload)
            state.subscribed_channels = set(sub_info["channel_ids"])
            state.udp_port = sub_info["udp_port"]
            if not state.subscribed_channels:
                # Empty subscription = subscribe to all
                state.subscribed_channels = {ch.channel_id for ch in self.channels}
            conn.sendall(encode_subscribed(list(state.subscribed_channels)))

            # Register client
            with self._clients_lock:
                self._clients[addr_str] = state
            if self._on_connected:
                self._on_connected(addr_str)
            logger.info("Client %s subscribed to %d channels", addr_str, len(state.subscribed_channels))

            # Ongoing control message loop
            conn.settimeout(_POLL_TIMEOUT)
            while not self._stop_event.is_set():
                msg = self._recv_ctrl_msg(conn)
                if msg is False:
                    continue  # timeout, no data yet
                if msg is None:
                    break  # EOF
                msg_type, payload = msg
                self._dispatch_ctrl(state, msg_type, payload)

        except (OSError, ValueError):
            if not self._stop_event.is_set():
                logger.debug("Client %s error", addr_str, exc_info=True)
        finally:
            self._remove_client(addr_str, conn)

    def _dispatch_ctrl(
        self, state: _ClientState, msg_type: MsgType, payload: bytes
    ) -> None:
        """Handle one control message from a connected client."""
        if msg_type == MsgType.PING:
            ts = payload[0:8]  # raw timestamp bytes
            try:
                conn = state.sock
                assert conn is not None
                conn.sendall(encode_pong(
                    __import__("struct").unpack_from("<d", payload)[0]
                ))
            except OSError:
                pass
        elif msg_type == MsgType.PONG:
            state.last_pong = time.monotonic()
        elif msg_type == MsgType.DISCONNECT:
            logger.info("Client %s sent DISCONNECT", state.address)
            raise OSError("client disconnected")
        else:
            logger.debug("Unhandled control msg 0x%02X from %s", int(msg_type), state.address)

    def _keepalive_loop(self) -> None:
        """Send PING to all clients; evict those that haven't replied."""
        while not self._stop_event.is_set():
            self._stop_event.wait(HEARTBEAT_INTERVAL)
            now = time.monotonic()
            ts = __import__("time").time()
            ping_msg = encode_ping(ts)
            stale: list[str] = []
            with self._clients_lock:
                clients = list(self._clients.values())
            for client in clients:
                if now - client.last_pong > HEARTBEAT_TIMEOUT:
                    stale.append(client.address)
                    continue
                try:
                    assert client.sock is not None
                    client.sock.sendall(ping_msg)
                except OSError:
                    stale.append(client.address)
            for addr in stale:
                logger.warning("Evicting stale client: %s", addr)
                with self._clients_lock:
                    c = self._clients.pop(addr, None)
                if c and c.sock:
                    try:
                        c.sock.close()
                    except OSError:
                        pass
                if self._on_disconnected:
                    self._on_disconnected(addr)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _recv_ctrl_msg(conn: socket.socket) -> tuple[MsgType, bytes] | None | bool:
        """Read one framed control message from *conn*.

        Returns a ``(MsgType, payload)`` tuple on success, ``False`` on timeout
        (no data yet), or ``None`` on EOF / parse error.
        """
        from .protocol import _CTRL_HDR_SIZE, _CTRL_HDR_FMT, STREAM_MAGIC
        import struct as _struct

        try:
            header = _recvall(conn, _CTRL_HDR_SIZE)
            if header is False:
                return False
            if not header:
                return None
            magic, length, msg_type_raw = _struct.unpack_from(_CTRL_HDR_FMT, header)
            if magic != STREAM_MAGIC:
                return None
            payload = _recvall(conn, length) if length else b""
            if payload is False or payload is None:
                return None
            return MsgType(msg_type_raw), payload
        except (OSError, ValueError):
            return None

    def _remove_client(self, addr_str: str, conn: socket.socket) -> None:
        """Remove a client from the registry and close its socket."""
        with self._clients_lock:
            self._clients.pop(addr_str, None)
        try:
            conn.close()
        except OSError:
            pass
        if self._on_disconnected:
            self._on_disconnected(addr_str)
        logger.info("Client disconnected: %s", addr_str)

    def _broadcast_ctrl(self, msg: bytes) -> None:
        """Send a control message to all connected clients (best-effort)."""
        with self._clients_lock:
            clients = list(self._clients.values())
        for client in clients:
            try:
                assert client.sock is not None
                client.sock.sendall(msg)
            except OSError:
                pass

    def _broadcast_disconnect(self, reason: DisconnectReason) -> None:
        """Send DISCONNECT to all clients."""
        self._broadcast_ctrl(encode_disconnect(reason))


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
