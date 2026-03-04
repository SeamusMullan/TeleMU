"""Telemetry streaming wire protocol constants and frame structures.

Implements the TeleMU streaming protocol v2 as documented in
``docs/docs/streaming/protocol.md``.

Wire format — all multi-byte integers are little-endian.

TCP control channel (default port 9101)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Every message starts with a 7-byte header::

    Offset  Size  Field
    0       4     magic: b"TMU\\x02"
    4       2     length: uint16 (payload bytes that follow)
    6       1     msg_type: uint8

Followed by *length* payload bytes specific to each message type.

UDP telemetry channel (default port 9100)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    Offset  Size  Field
    0       4     magic: b"TMU\\x02"
    4       4     session_id: uint32
    8       4     sequence:   uint32 (monotonic; used for loss detection)
    12      8     timestamp:  float64
    20      2     channel_count: uint16
    22+     10×N  channel data (channel_id: uint16, value: float64) per channel

Discovery UDP broadcast (port 9099)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    Offset  Size  Field
    0       4     magic: b"TMU\\x02"
    4       2     version: uint16
    6       1     msg_type: 0x01
    7       32    driver_name: UTF-8, null-padded
    39      64    track_name:  UTF-8, null-padded
    103     64    vehicle_name: UTF-8, null-padded
    167     1     session_type: uint8
    168     2     tcp_port: uint16
    170     2     udp_port: uint16
    172     4     session_id: uint32
"""

from __future__ import annotations

import struct

# ── Magic & version ───────────────────────────────────────────────────────────

MAGIC: bytes = b"TMU\x02"
PROTOCOL_VERSION: int = 1

# ── Default ports ─────────────────────────────────────────────────────────────

DEFAULT_TCP_PORT: int = 9101   # control channel
DEFAULT_UDP_PORT: int = 9100   # telemetry data channel
DISCOVERY_PORT: int = 9099     # UDP discovery broadcast

# ── Heartbeat tuning ──────────────────────────────────────────────────────────

HEARTBEAT_TIMEOUT: float = 5.0  # seconds without PING before disconnect

# ── Control message types ─────────────────────────────────────────────────────

MSG_HELLO = 0x10          # Client → Server: client_name (32), protocol_version (2)
MSG_WELCOME = 0x11        # Server → Client: session_id (4), channel_count (2), channels
MSG_SUBSCRIBE = 0x12      # Client → Server: channel_mask (bitfield)
MSG_SUBSCRIBED = 0x13     # Server → Client: active_channels (bitfield)
MSG_SESSION_UPDATE = 0x14 # Server → Client: track (64), vehicle (64), session_type (1)
MSG_PING = 0x15           # Either → Either: timestamp (8)
MSG_PONG = 0x16           # Either → Either: echo timestamp (8)
MSG_DISCONNECT = 0x1F     # Either → Either: reason (1)

# Discovery packet message type
MSG_DISCOVERY = 0x01

# Disconnect reason codes
DISCONNECT_NORMAL = 0
DISCONNECT_VERSION_MISMATCH = 1
DISCONNECT_SESSION_END = 2

# ── Struct definitions ────────────────────────────────────────────────────────

# TCP control message header: magic(4s) length(H) msg_type(B)
CTRL_HDR: struct.Struct = struct.Struct("<4sHB")
CTRL_HDR_SIZE: int = CTRL_HDR.size  # 7

# HELLO payload: client_name(32s) protocol_version(H)
HELLO_FMT: struct.Struct = struct.Struct("<32sH")

# WELCOME base payload: session_id(I) channel_count(H)
WELCOME_BASE_FMT: struct.Struct = struct.Struct("<IH")

# Each channel entry in WELCOME: channel_id(H) name(32s) unit(16s) type(B) min(d) max(d)
CHANNEL_ENTRY_FMT: struct.Struct = struct.Struct("<H32s16sBdd")
CHANNEL_ENTRY_SIZE: int = CHANNEL_ENTRY_FMT.size  # 67

# PING / PONG payload: timestamp(d)
PING_FMT: struct.Struct = struct.Struct("<d")

# DISCONNECT payload: reason(B)
DISCONNECT_FMT: struct.Struct = struct.Struct("<B")

# UDP telemetry frame header:
# magic(4s) session_id(I) sequence(I) timestamp(d) channel_count(H)
UDP_HDR_FMT: struct.Struct = struct.Struct("<4sIIdH")
UDP_HDR_SIZE: int = UDP_HDR_FMT.size  # 22

# Per-channel value in a UDP frame: channel_id(H) value(d)
UDP_CH_FMT: struct.Struct = struct.Struct("<Hd")
UDP_CH_SIZE: int = UDP_CH_FMT.size  # 10

# Discovery packet: magic(4s) version(H) msg_type(B) driver_name(32s)
# track_name(64s) vehicle_name(64s) session_type(B) tcp_port(H) udp_port(H) session_id(I)
DISCOVERY_FMT: struct.Struct = struct.Struct("<4sHB32s64s64sBHHI")
DISCOVERY_SIZE: int = DISCOVERY_FMT.size  # 176


# ── Helpers ───────────────────────────────────────────────────────────────────


def pack_ctrl(msg_type: int, payload: bytes) -> bytes:
    """Serialize a TCP control message (header + payload)."""
    return CTRL_HDR.pack(MAGIC, len(payload), msg_type) + payload


def pack_hello(client_name: str = "TeleMU-engineer") -> bytes:
    """Build a HELLO message payload."""
    name_b = client_name.encode()[:31].ljust(32, b"\x00")
    payload = HELLO_FMT.pack(name_b, PROTOCOL_VERSION)
    return pack_ctrl(MSG_HELLO, payload)


def pack_subscribe(channel_count: int, subscribe_all: bool = True) -> bytes:
    """Build a SUBSCRIBE message payload (bitfield, all channels by default)."""
    n_bytes = (channel_count + 7) // 8
    if subscribe_all:
        mask = bytes([0xFF] * n_bytes)
    else:
        mask = bytes(n_bytes)
    return pack_ctrl(MSG_SUBSCRIBE, mask)


def pack_pong(timestamp: float) -> bytes:
    """Build a PONG response payload."""
    return pack_ctrl(MSG_PONG, PING_FMT.pack(timestamp))


def parse_udp_frame(data: bytes) -> tuple[int, int, float, dict[str, float]] | None:
    """Parse a UDP telemetry frame.

    Returns:
        ``(session_id, sequence, timestamp, channels)`` or ``None`` if invalid.
    """
    if len(data) < UDP_HDR_SIZE:
        return None

    magic, session_id, seq, ts, ch_count = UDP_HDR_FMT.unpack(data[:UDP_HDR_SIZE])
    if magic != MAGIC:
        return None

    expected_len = UDP_HDR_SIZE + ch_count * UDP_CH_SIZE
    if len(data) < expected_len:
        return None

    channels: dict[str, float] = {}
    offset = UDP_HDR_SIZE
    for _ in range(ch_count):
        ch_id, value = UDP_CH_FMT.unpack(data[offset : offset + UDP_CH_SIZE])
        channels[str(ch_id)] = value
        offset += UDP_CH_SIZE

    return session_id, seq, ts, channels


def parse_discovery(data: bytes) -> dict | None:
    """Parse a UDP discovery packet.

    Returns a dict with driver info or ``None`` if invalid.
    """
    if len(data) < DISCOVERY_SIZE:
        return None
    magic, version, msg_type, drv_b, trk_b, veh_b, stype, tcp_port, udp_port, sid = (
        DISCOVERY_FMT.unpack(data[:DISCOVERY_SIZE])
    )
    if magic != MAGIC or msg_type != MSG_DISCOVERY:
        return None
    return {
        "version": version,
        "driver_name": drv_b.rstrip(b"\x00").decode(errors="replace"),
        "track_name": trk_b.rstrip(b"\x00").decode(errors="replace"),
        "vehicle_name": veh_b.rstrip(b"\x00").decode(errors="replace"),
        "session_type": stype,
        "tcp_port": tcp_port,
        "udp_port": udp_port,
        "session_id": sid,
    }
