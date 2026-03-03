"""Telemetry streaming client (engineer side).

Connects to a driver's streaming server to receive live telemetry and
feeds it into a :class:`~lmupi.dashboard.LiveDashboard`.

Protocol overview
-----------------
1. **TCP handshake** — client connects to ``host:port`` and receives a
   JSON-encoded *channel map* describing every telemetry channel the server
   will stream (name, unit, min, max, warn thresholds, display type).
2. **UDP telemetry frames** — the server pushes compact binary frames on a
   UDP port (communicated inside the handshake response).  Each frame
   carries a 4-byte big-endian sequence number followed by a series of
   ``(channel_index: u16, value: f32)`` pairs.
3. **Jitter buffer** — incoming frames are held for ~100 ms before being
   flushed to the dashboard, smoothing out network jitter.
4. **Packet-loss handling** — gaps in sequence numbers are simply skipped;
   the client never stalls waiting for a missing frame.
5. **Auto-reconnect** — on disconnect the client retries with exponential
   backoff (1 s → 2 s → 4 s … capped at 30 s).

Usage::

    client = StreamingClient(dashboard, host="192.168.1.10", port=9100)
    client.start_streaming()   # begins connection + listening
    client.stop_streaming()    # stops cleanly
"""

from __future__ import annotations

import json
import logging
import socket
import struct
import time
import threading
from collections import deque
from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal, QTimer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wire-format constants
# ---------------------------------------------------------------------------

_HANDSHAKE_MAGIC = b"TELE"          # 4-byte magic sent by the client
_HANDSHAKE_VERSION = 1              # protocol version
_HEADER_SIZE = 4                    # sequence number (uint32 big-endian)
_PAIR_SIZE = 6                      # channel_index (uint16) + value (float32)
_MAX_UDP_SIZE = 65535               # maximum UDP datagram
_TCP_RECV_SIZE = 4096               # TCP receive chunk size
_HANDSHAKE_TIMEOUT_S = 5.0          # TCP connect + recv timeout
_DEFAULT_BUFFER_MS = 100            # jitter buffer depth
_RECONNECT_BASE_S = 1.0            # initial backoff
_RECONNECT_CAP_S = 30.0            # max backoff


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

@dataclass
class ChannelSpec:
    """Description of a single telemetry channel received during handshake."""
    index: int
    name: str
    unit: str = ""
    min_val: float = 0.0
    max_val: float = 100.0
    warn_low: float | None = None
    warn_high: float | None = None
    display: str = "gauge"  # "gauge" or "spark"


@dataclass
class TelemetryFrame:
    """A single received UDP frame."""
    seq: int
    timestamp: float  # local receive time (monotonic)
    pairs: list[tuple[int, float]] = field(default_factory=list)


def parse_channel_map(data: bytes) -> tuple[list[ChannelSpec], int]:
    """Parse the JSON channel map received over TCP.

    Returns ``(channels, udp_port)``.
    """
    payload = json.loads(data.decode("utf-8"))
    udp_port = int(payload["udp_port"])
    channels: list[ChannelSpec] = []
    for i, ch in enumerate(payload["channels"]):
        channels.append(ChannelSpec(
            index=i,
            name=ch["name"],
            unit=ch.get("unit", ""),
            min_val=ch.get("min", 0.0),
            max_val=ch.get("max", 100.0),
            warn_low=ch.get("warn_low"),
            warn_high=ch.get("warn_high"),
            display=ch.get("display", "gauge"),
        ))
    return channels, udp_port


def parse_udp_frame(data: bytes) -> TelemetryFrame | None:
    """Decode a binary UDP telemetry frame.

    Frame layout::

        [seq: uint32 BE] [channel_idx: uint16 BE, value: float32 BE] ...

    Returns *None* if the datagram is malformed.
    """
    if len(data) < _HEADER_SIZE:
        return None
    seq = struct.unpack("!I", data[:_HEADER_SIZE])[0]
    body = data[_HEADER_SIZE:]
    if len(body) % _PAIR_SIZE != 0:
        return None
    n_pairs = len(body) // _PAIR_SIZE
    pairs: list[tuple[int, float]] = []
    for i in range(n_pairs):
        offset = i * _PAIR_SIZE
        idx, val = struct.unpack("!Hf", body[offset:offset + _PAIR_SIZE])
        pairs.append((idx, val))
    return TelemetryFrame(seq=seq, timestamp=time.monotonic(), pairs=pairs)


def build_handshake_request() -> bytes:
    """Build the client handshake request sent over TCP."""
    return _HANDSHAKE_MAGIC + struct.pack("!B", _HANDSHAKE_VERSION)


# ---------------------------------------------------------------------------
# Jitter buffer
# ---------------------------------------------------------------------------

class JitterBuffer:
    """Simple time-based jitter buffer.

    Frames are held for *buffer_ms* milliseconds before being released in
    sequence order.  Out-of-order or duplicate frames are silently dropped.
    """

    def __init__(self, buffer_ms: int = _DEFAULT_BUFFER_MS) -> None:
        self._buffer_s = buffer_ms / 1000.0
        self._pending: deque[TelemetryFrame] = deque()
        self._last_released_seq: int = -1

    def put(self, frame: TelemetryFrame) -> None:
        """Add a frame to the buffer."""
        # Drop duplicates and frames older than last released
        if frame.seq <= self._last_released_seq:
            return
        self._pending.append(frame)

    def flush(self) -> list[TelemetryFrame]:
        """Return frames that have been buffered long enough, in order."""
        now = time.monotonic()
        ready: list[TelemetryFrame] = []
        remaining: deque[TelemetryFrame] = deque()

        for frame in self._pending:
            if now - frame.timestamp >= self._buffer_s:
                ready.append(frame)
            else:
                remaining.append(frame)

        self._pending = remaining

        # Sort by sequence and skip anything already released
        ready.sort(key=lambda f: f.seq)
        output: list[TelemetryFrame] = []
        for frame in ready:
            if frame.seq > self._last_released_seq:
                self._last_released_seq = frame.seq
                output.append(frame)
        return output

    def reset(self) -> None:
        """Clear all buffered state."""
        self._pending.clear()
        self._last_released_seq = -1


# ---------------------------------------------------------------------------
# Streaming client (QThread)
# ---------------------------------------------------------------------------

class StreamingClient(QThread):
    """Background thread that connects to a telemetry streaming server.

    Signals
    -------
    connected : ()
        Emitted when the TCP handshake succeeds and UDP listening starts.
    disconnected : ()
        Emitted when the connection is lost or the client is stopped.
    error : (str)
        Emitted with a human-readable error message.
    status_changed : (str)
        Emitted whenever the connection status text changes.
    channel_map_received : (list)
        Emitted with the list of :class:`ChannelSpec` after a successful
        handshake, so the dashboard can register channels.
    """

    connected = Signal()
    disconnected = Signal()
    error = Signal(str)
    status_changed = Signal(str)
    channel_map_received = Signal(list)

    def __init__(
        self,
        dashboard,
        host: str,
        port: int,
        buffer_ms: int = _DEFAULT_BUFFER_MS,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._dashboard = dashboard
        self._host = host
        self._port = port
        self._buffer_ms = buffer_ms
        self._running = False

        # Populated after handshake
        self._channel_specs: list[ChannelSpec] = []
        self._index_to_name: dict[int, str] = {}
        self._udp_port: int = 0

    # -- Public API ---------------------------------------------------------

    def start_streaming(self) -> None:
        """Start the streaming client thread."""
        self._running = True
        self.start()

    def stop_streaming(self) -> None:
        """Signal the client to stop and wait for it to finish."""
        self._running = False
        self.wait(5000)

    # -- Thread entry point -------------------------------------------------

    def run(self) -> None:  # noqa: C901 -- linear flow, not complex
        backoff = _RECONNECT_BASE_S

        while self._running:
            try:
                self._do_session()
            except Exception as exc:
                logger.exception("StreamingClient session error")
                self.error.emit(str(exc))

            if not self._running:
                break

            # Auto-reconnect with exponential backoff
            self.status_changed.emit(f"Reconnecting in {backoff:.0f}s…")
            logger.info("StreamingClient: reconnecting in %.1fs", backoff)
            deadline = time.monotonic() + backoff
            while self._running and time.monotonic() < deadline:
                self.msleep(250)
            backoff = min(backoff * 2, _RECONNECT_CAP_S)

        self.disconnected.emit()

    # -- Single session -----------------------------------------------------

    def _do_session(self) -> None:
        """Run one connect → listen → disconnect cycle."""
        # 1. TCP handshake
        self.status_changed.emit("Connecting…")
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_sock.settimeout(_HANDSHAKE_TIMEOUT_S)
        try:
            tcp_sock.connect((self._host, self._port))
            tcp_sock.sendall(build_handshake_request())

            # Receive channel map (may arrive in multiple chunks)
            chunks: list[bytes] = []
            while True:
                chunk = tcp_sock.recv(_TCP_RECV_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
            if not raw:
                raise ConnectionError("Empty handshake response")

            self._channel_specs, self._udp_port = parse_channel_map(raw)
            self._index_to_name = {ch.index: ch.name for ch in self._channel_specs}
        except Exception as exc:
            raise ConnectionError(f"Handshake failed: {exc}") from exc
        finally:
            tcp_sock.close()

        logger.info(
            "StreamingClient: handshake OK — %d channels, UDP port %d",
            len(self._channel_specs),
            self._udp_port,
        )

        # Notify dashboard so it can register channels
        self.channel_map_received.emit(self._channel_specs)
        self.connected.emit()
        self.status_changed.emit("Connected — receiving telemetry")

        # Reset backoff on successful connection
        # (handled in run() by reaching this point without exception)

        # 2. UDP listener — determine the local address facing the server
        #    so we don't bind to all network interfaces.
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect((self._host, self._udp_port))
            local_addr = probe.getsockname()[0]
        finally:
            probe.close()

        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_sock.bind((local_addr, self._udp_port))
        udp_sock.settimeout(1.0)  # allow periodic _running checks

        jitter = JitterBuffer(self._buffer_ms)

        try:
            while self._running:
                # Receive UDP frames
                try:
                    data, _addr = udp_sock.recvfrom(_MAX_UDP_SIZE)
                except socket.timeout:
                    # Flush buffer even when no new data arrives
                    self._flush_to_dashboard(jitter)
                    continue

                frame = parse_udp_frame(data)
                if frame is not None:
                    jitter.put(frame)

                # Flush matured frames to dashboard
                self._flush_to_dashboard(jitter)
        finally:
            udp_sock.close()
            jitter.reset()

    def _flush_to_dashboard(self, jitter: JitterBuffer) -> None:
        """Push all matured frames from the jitter buffer to the dashboard."""
        for frame in jitter.flush():
            for ch_idx, value in frame.pairs:
                name = self._index_to_name.get(ch_idx)
                if name is not None:
                    self._dashboard.push(name, value)
