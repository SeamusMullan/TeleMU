"""Telemetry streaming server — broadcasts live telemetry over the network.

Architecture
============
* Runs alongside TelemetryReader as a separate QThread.
* **TCP listener** accepts client connections, performs handshake, and handles
  channel subscription negotiation and heartbeats.
* **UDP sender** broadcasts (or unicasts) telemetry frames to connected clients.
* Configurable port (default 19740) and bind address.

Usage::

    server = TelemetryStreamingServer(port=19740)
    server.start_server()          # begins listening
    server.broadcast_telemetry({"Speed": 280.5, "RPM": 7200.0, ...})
    server.stop_server()
"""

from __future__ import annotations

import json
import logging
import select
import socket
import threading
import time
from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal

from lmupi.streaming.protocol import (
    DEFAULT_PORT,
    MsgType,
    TCP_HEADER_SIZE,
    pack_control_message,
    pack_telemetry_frame,
    unpack_control_message,
)

logger = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL = 5.0   # seconds between heartbeats
_CLIENT_TIMEOUT = 15.0      # drop client after this many seconds without heartbeat


@dataclass
class _ClientInfo:
    """Tracks a connected client."""
    addr: tuple[str, int]          # TCP address
    udp_addr: tuple[str, int]      # where to send UDP frames
    tcp_sock: socket.socket
    name: str = ""
    subscribed_channels: set[str] = field(default_factory=set)
    subscribe_all: bool = True
    last_heartbeat: float = field(default_factory=time.time)


class TelemetryStreamingServer(QThread):
    """Background thread that accepts clients via TCP and broadcasts telemetry via UDP.

    Signals:
        server_started: emitted when the server begins listening.
        server_stopped: emitted when the server shuts down.
        client_connected(str): emitted with client description on connect.
        client_disconnected(str): emitted with client description on disconnect.
        error(str): emitted with an error message.
        status_update(int, float): emitted periodically with (client_count, data_rate_bytes_per_sec).
    """

    server_started = Signal()
    server_stopped = Signal()
    client_connected = Signal(str)
    client_disconnected = Signal(str)
    error = Signal(str)
    status_update = Signal(int, float)  # client_count, bytes/sec

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        bind_address: str = "0.0.0.0",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._port = port
        self._bind_address = bind_address

        self._running = False
        self._clients: dict[tuple[str, int], _ClientInfo] = {}  # keyed by TCP addr
        self._clients_lock = threading.Lock()

        self._sequence = 0
        self._bytes_sent = 0
        self._bytes_sent_window_start = 0.0

        # Available channel names — updated each broadcast
        self._available_channels: list[str] = []

        # Sockets (created in run())
        self._tcp_sock: socket.socket | None = None
        self._udp_sock: socket.socket | None = None

    # -- Public API --

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        if self._running:
            raise RuntimeError("Cannot change port while server is running")
        self._port = value

    @property
    def bind_address(self) -> str:
        return self._bind_address

    @bind_address.setter
    def bind_address(self, value: str) -> None:
        if self._running:
            raise RuntimeError("Cannot change bind address while server is running")
        self._bind_address = value

    @property
    def client_count(self) -> int:
        with self._clients_lock:
            return len(self._clients)

    def start_server(self) -> None:
        """Start the server thread."""
        self._running = True
        self.start()

    def stop_server(self) -> None:
        """Signal the server to stop and wait for it to finish."""
        self._running = False
        # Poke the TCP socket so select() returns immediately
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((self._bind_address if self._bind_address != "0.0.0.0" else "127.0.0.1", self._port))
            s.close()
        except OSError:
            pass
        self.wait(3000)

    def broadcast_telemetry(self, channels: dict[str, float]) -> None:
        """Send a telemetry frame to all connected clients.

        This is meant to be called from the TelemetryReader thread or the
        dashboard's data push path.

        Args:
            channels: Mapping of channel name → value.
        """
        if not self._running or self._udp_sock is None:
            return

        self._available_channels = list(channels.keys())
        self._sequence += 1

        with self._clients_lock:
            if not self._clients:
                return

            for client in list(self._clients.values()):
                # Filter channels by client subscription
                if client.subscribe_all:
                    data = channels
                else:
                    data = {k: v for k, v in channels.items() if k in client.subscribed_channels}

                if not data:
                    continue

                packet = pack_telemetry_frame(self._sequence, data)

                try:
                    self._udp_sock.sendto(packet, client.udp_addr)
                    self._bytes_sent += len(packet)
                except OSError as exc:
                    logger.debug("UDP send failed for %s: %s", client.udp_addr, exc)

    # -- Thread main loop --

    def run(self) -> None:
        """Server main loop — runs in a background QThread."""
        try:
            self._setup_sockets()
        except OSError as exc:
            self.error.emit(f"Could not bind to {self._bind_address}:{self._port}: {exc}")
            return

        self.server_started.emit()
        logger.info("Streaming server listening on %s:%d", self._bind_address, self._port)

        self._bytes_sent = 0
        self._bytes_sent_window_start = time.time()

        try:
            while self._running:
                self._accept_loop_tick()
                self._check_heartbeats()
                self._emit_status()
        except Exception as exc:
            self.error.emit(f"Server error: {exc}")
            logger.exception("Streaming server error")
        finally:
            self._teardown()

    # -- Socket setup / teardown --

    def _setup_sockets(self) -> None:
        self._tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_sock.setblocking(False)
        self._tcp_sock.bind((self._bind_address, self._port))
        self._tcp_sock.listen(8)

        self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp_sock.bind((self._bind_address, 0))  # ephemeral port for sending

    def _teardown(self) -> None:
        # Notify clients
        with self._clients_lock:
            for client in list(self._clients.values()):
                self._send_goodbye(client)
            self._clients.clear()

        if self._tcp_sock is not None:
            try:
                self._tcp_sock.close()
            except OSError:
                pass
            self._tcp_sock = None

        if self._udp_sock is not None:
            try:
                self._udp_sock.close()
            except OSError:
                pass
            self._udp_sock = None

        self._running = False
        self.server_stopped.emit()
        logger.info("Streaming server stopped")

    # -- Accept loop --

    def _accept_loop_tick(self) -> None:
        """One iteration: accept new TCP connections, read control messages."""
        if self._tcp_sock is None:
            return

        # Gather all readable sockets
        read_sockets = [self._tcp_sock]
        with self._clients_lock:
            read_sockets.extend(c.tcp_sock for c in self._clients.values())

        try:
            readable, _, _ = select.select(read_sockets, [], [], 0.2)
        except (OSError, ValueError):
            return

        for sock in readable:
            if sock is self._tcp_sock:
                self._accept_client()
            else:
                self._handle_client_data(sock)

    def _accept_client(self) -> None:
        """Accept a new TCP connection and perform handshake."""
        if self._tcp_sock is None:
            return
        try:
            conn, addr = self._tcp_sock.accept()
        except OSError:
            return

        conn.setblocking(False)
        conn.settimeout(2.0)

        try:
            # Read handshake request
            header = self._recv_exact(conn, TCP_HEADER_SIZE)
            if header is None:
                conn.close()
                return

            _, _, payload_len = header[0], header[1], int.from_bytes(header[2:6], "big")
            body = self._recv_exact(conn, payload_len) if payload_len > 0 else b""
            if body is None:
                conn.close()
                return

            msg_type, payload = unpack_control_message(header + (body or b""))

            if msg_type != MsgType.HANDSHAKE_REQ:
                conn.close()
                return

            client_name = payload.get("client_name", f"{addr[0]}:{addr[1]}")

            # UDP target: same IP as TCP, port from payload or TCP port + 1
            udp_port = payload.get("udp_port", addr[1])
            udp_addr = (addr[0], udp_port)

            conn.setblocking(False)

            client = _ClientInfo(
                addr=addr,
                udp_addr=udp_addr,
                tcp_sock=conn,
                name=client_name,
            )

            with self._clients_lock:
                self._clients[addr] = client

            # Send handshake ACK
            ack = pack_control_message(MsgType.HANDSHAKE_ACK, {
                "channels": self._available_channels,
                "udp_port": self._udp_sock.getsockname()[1] if self._udp_sock else 0,
            })
            try:
                conn.sendall(ack)
            except OSError:
                pass

            desc = f"{client_name} ({addr[0]}:{addr[1]})"
            self.client_connected.emit(desc)
            logger.info("Client connected: %s", desc)

        except Exception as exc:
            logger.debug("Handshake failed from %s: %s", addr, exc)
            try:
                conn.close()
            except OSError:
                pass

    def _handle_client_data(self, sock: socket.socket) -> None:
        """Read and process a control message from an existing client."""
        addr = sock.getpeername()
        with self._clients_lock:
            client = self._clients.get(addr)
        if client is None:
            return

        try:
            header = self._recv_exact(sock, TCP_HEADER_SIZE)
            if header is None:
                self._remove_client(addr, reason="connection closed")
                return

            _, _, payload_len = header[0], header[1], int.from_bytes(header[2:6], "big")
            body = self._recv_exact(sock, payload_len) if payload_len > 0 else b""
            if body is None:
                self._remove_client(addr, reason="truncated message")
                return

            msg_type, payload = unpack_control_message(header + (body or b""))

        except (OSError, ValueError) as exc:
            self._remove_client(addr, reason=str(exc))
            return

        if msg_type == MsgType.HEARTBEAT:
            with self._clients_lock:
                if addr in self._clients:
                    self._clients[addr].last_heartbeat = time.time()
            # Echo heartbeat back
            try:
                sock.sendall(pack_control_message(MsgType.HEARTBEAT))
            except OSError:
                pass

        elif msg_type == MsgType.CHANNEL_SUB:
            ch_list = payload.get("channels", [])
            with self._clients_lock:
                if addr in self._clients:
                    if ch_list:
                        self._clients[addr].subscribed_channels = set(ch_list)
                        self._clients[addr].subscribe_all = False
                    else:
                        self._clients[addr].subscribe_all = True
            logger.info("Client %s subscribed to %s", addr, ch_list or "all")

        elif msg_type == MsgType.GOODBYE:
            self._remove_client(addr, reason="goodbye")

    def _remove_client(self, addr: tuple[str, int], reason: str = "") -> None:
        with self._clients_lock:
            client = self._clients.pop(addr, None)
        if client is None:
            return
        try:
            client.tcp_sock.close()
        except OSError:
            pass
        desc = f"{client.name} ({addr[0]}:{addr[1]})"
        self.client_disconnected.emit(desc)
        logger.info("Client disconnected: %s (%s)", desc, reason)

    def _send_goodbye(self, client: _ClientInfo) -> None:
        try:
            client.tcp_sock.sendall(pack_control_message(MsgType.GOODBYE))
        except OSError:
            pass
        try:
            client.tcp_sock.close()
        except OSError:
            pass

    # -- Heartbeat / status --

    def _check_heartbeats(self) -> None:
        now = time.time()
        with self._clients_lock:
            stale = [
                addr for addr, c in self._clients.items()
                if now - c.last_heartbeat > _CLIENT_TIMEOUT
            ]
        for addr in stale:
            self._remove_client(addr, reason="heartbeat timeout")

    def _emit_status(self) -> None:
        now = time.time()
        elapsed = now - self._bytes_sent_window_start
        if elapsed >= 1.0:
            rate = self._bytes_sent / elapsed
            self._bytes_sent = 0
            self._bytes_sent_window_start = now
            self.status_update.emit(self.client_count, rate)

    # -- Helpers --

    @staticmethod
    def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
        """Receive exactly *n* bytes from *sock*, or ``None`` on failure."""
        if n == 0:
            return b""
        buf = bytearray()
        while len(buf) < n:
            try:
                chunk = sock.recv(n - len(buf))
            except (BlockingIOError, socket.timeout):
                # For non-blocking sockets, wait briefly
                try:
                    select.select([sock], [], [], 1.0)
                except (OSError, ValueError):
                    return None
                continue
            except OSError:
                return None
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)
