"""Telemetry streaming protocol — packet formats and (de)serialization.

Wire formats
============

UDP telemetry frame (< 1400 bytes to avoid fragmentation)
---------------------------------------------------------
Offset  Size  Field
0       1     version          (uint8)
1       1     msg_type         (uint8, always MSG_TELEMETRY_FRAME)
2       4     sequence         (uint32 big-endian)
6       8     timestamp        (float64 big-endian, seconds since epoch)
14      2     channel_count    (uint16 big-endian)
16      2     payload_len      (uint16 big-endian, length of compressed payload)
18      ...   payload          (LZ4-compressed channel data)

Compressed payload layout (before compression):
  For each channel:
    1 byte   name_len
    N bytes  name (UTF-8)
    8 bytes  value (float64 big-endian)

TCP control message
-------------------
Offset  Size  Field
0       1     version          (uint8)
1       1     msg_type         (uint8)
2       4     payload_len      (uint32 big-endian)
6       ...   payload          (JSON-encoded UTF-8)

Control message types
---------------------
HANDSHAKE_REQ    client → server  {"client_name": "..."}
HANDSHAKE_ACK    server → client  {"channels": [...], "udp_port": N}
CHANNEL_SUB      client → server  {"channels": [...]}  (subscribe to subset)
HEARTBEAT        bidirectional    {}
GOODBYE          bidirectional    {}
"""

from __future__ import annotations

import enum
import json
import struct
import time

try:
    import lz4.frame as _lz4

    def _compress(data: bytes) -> bytes:
        return _lz4.compress(data)

    def _decompress(data: bytes) -> bytes:
        return _lz4.decompress(data)

except ImportError:
    import zlib

    def _compress(data: bytes) -> bytes:  # type: ignore[misc]
        return zlib.compress(data, level=1)

    def _decompress(data: bytes) -> bytes:  # type: ignore[misc]
        return zlib.decompress(data)


PROTOCOL_VERSION: int = 1
DEFAULT_PORT: int = 19740

# Struct formats
_UDP_HEADER = struct.Struct("!BBIdHH")   # version, type, seq, timestamp, ch_count, payload_len
_TCP_HEADER = struct.Struct("!BBI")      # version, type, payload_len
_CHANNEL_VALUE = struct.Struct("!d")     # float64 big-endian


class MsgType(enum.IntEnum):
    """Protocol message types."""
    TELEMETRY_FRAME = 0x01
    HANDSHAKE_REQ   = 0x10
    HANDSHAKE_ACK   = 0x11
    CHANNEL_SUB     = 0x12
    HEARTBEAT       = 0x20
    GOODBYE         = 0x30


# ---------------------------------------------------------------------------
# UDP telemetry frame
# ---------------------------------------------------------------------------

def pack_telemetry_frame(
    sequence: int,
    channels: dict[str, float],
    timestamp: float | None = None,
) -> bytes:
    """Serialize a telemetry frame into a UDP packet (< 1400 bytes).

    Args:
        sequence: Monotonically increasing packet counter.
        channels: Mapping of channel name → current value.
        timestamp: Seconds since epoch; defaults to ``time.time()``.

    Returns:
        The raw bytes ready to send via UDP.
    """
    if timestamp is None:
        timestamp = time.time()

    # Build uncompressed payload
    parts: list[bytes] = []
    for name, value in channels.items():
        name_bytes = name.encode("utf-8")
        if len(name_bytes) > 255:
            name_bytes = name_bytes[:255]
        parts.append(struct.pack("B", len(name_bytes)))
        parts.append(name_bytes)
        parts.append(_CHANNEL_VALUE.pack(value))
    raw_payload = b"".join(parts)

    compressed = _compress(raw_payload)

    header = _UDP_HEADER.pack(
        PROTOCOL_VERSION,
        MsgType.TELEMETRY_FRAME,
        sequence & 0xFFFFFFFF,
        timestamp,
        len(channels),
        len(compressed),
    )
    return header + compressed


def unpack_telemetry_frame(data: bytes) -> tuple[int, float, dict[str, float]]:
    """Deserialize a UDP telemetry frame.

    Returns:
        (sequence, timestamp, channels_dict)

    Raises:
        ValueError: If the packet is malformed.
    """
    if len(data) < _UDP_HEADER.size:
        raise ValueError("Packet too short for header")

    version, msg_type, seq, ts, ch_count, payload_len = _UDP_HEADER.unpack_from(data)

    if version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version {version}")
    if msg_type != MsgType.TELEMETRY_FRAME:
        raise ValueError(f"Expected TELEMETRY_FRAME, got {msg_type:#x}")

    compressed = data[_UDP_HEADER.size: _UDP_HEADER.size + payload_len]
    if len(compressed) != payload_len:
        raise ValueError("Truncated payload")

    raw = _decompress(compressed)

    channels: dict[str, float] = {}
    offset = 0
    for _ in range(ch_count):
        name_len = raw[offset]
        offset += 1
        name = raw[offset: offset + name_len].decode("utf-8")
        offset += name_len
        (value,) = _CHANNEL_VALUE.unpack_from(raw, offset)
        offset += _CHANNEL_VALUE.size
        channels[name] = value

    return seq, ts, channels


# ---------------------------------------------------------------------------
# TCP control message
# ---------------------------------------------------------------------------

def pack_control_message(msg_type: MsgType, payload: dict | None = None) -> bytes:
    """Serialize a TCP control message.

    Args:
        msg_type: One of the control ``MsgType`` values.
        payload: JSON-serializable dict (default: empty ``{}``).

    Returns:
        Raw bytes including the 6-byte header.
    """
    body = json.dumps(payload or {}).encode("utf-8")
    header = _TCP_HEADER.pack(PROTOCOL_VERSION, msg_type, len(body))
    return header + body


def unpack_control_message(data: bytes) -> tuple[MsgType, dict]:
    """Deserialize a TCP control message.

    *data* must contain at least the 6-byte header plus the indicated payload.

    Returns:
        (msg_type, payload_dict)

    Raises:
        ValueError: If the message is malformed.
    """
    if len(data) < _TCP_HEADER.size:
        raise ValueError("Message too short for header")

    version, raw_type, payload_len = _TCP_HEADER.unpack_from(data)

    if version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version {version}")

    msg_type = MsgType(raw_type)
    body = data[_TCP_HEADER.size: _TCP_HEADER.size + payload_len]
    if len(body) != payload_len:
        raise ValueError("Truncated control payload")

    payload = json.loads(body.decode("utf-8")) if body else {}
    return msg_type, payload


TCP_HEADER_SIZE: int = _TCP_HEADER.size
