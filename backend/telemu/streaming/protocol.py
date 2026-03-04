"""TeleMU streaming protocol — wire format constants and packet codecs.

All multi-byte integers are **little-endian**.

Transport layout
----------------
Channel    Transport   Port   Purpose
---------  ----------  -----  ----------------------------------------
Discovery  UDP bcast   9099   Zero-config driver announcement (2 s interval)
Telemetry  UDP         9100   High-frequency frame data (~60 Hz)
Control    TCP         9101   Handshake, subscribe, session updates

Packet magic
------------
``b"TMU\\x02"`` — streaming protocol v2.
(v1 is the ``.tmu`` file format; keeping the namespaces separate.)

See docs/docs/streaming/protocol.md for full specification.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import lz4.frame

# ── Constants ────────────────────────────────────────────────────────────────

STREAM_MAGIC = b"TMU\x02"
STREAM_MAGIC_LEN = 4
PROTOCOL_VERSION: int = 2

DISCOVERY_PORT: int = 9099
TELEMETRY_PORT: int = 9100
CONTROL_PORT: int = 9101

# Maximum UDP payload to stay under MTU (Ethernet 1500 - 28 byte IP/UDP header)
MAX_UDP_PAYLOAD: int = 1400

# Heartbeat interval (seconds) — sent as PING over control channel
HEARTBEAT_INTERVAL: float = 5.0
# Seconds without a PONG before a client is considered stale
HEARTBEAT_TIMEOUT: float = 15.0


# ── Message types ────────────────────────────────────────────────────────────


class MsgType(IntEnum):
    """Control-channel message type identifiers."""

    # Discovery (UDP)
    DISCOVERY_ANNOUNCE = 0x01

    # Handshake (TCP, client → server)
    HELLO = 0x10
    # Handshake (TCP, server → client)
    WELCOME = 0x11
    # Subscription (TCP, client → server)
    SUBSCRIBE = 0x12
    # Subscription confirm (TCP, server → client)
    SUBSCRIBED = 0x13
    # Session metadata update (TCP, server → client)
    SESSION_UPDATE = 0x14
    # Keepalive (TCP, either direction)
    PING = 0x15
    PONG = 0x16
    # Graceful disconnect (TCP, either direction)
    DISCONNECT = 0x1F


class DisconnectReason(IntEnum):
    """Reason codes for DISCONNECT messages."""

    NORMAL = 0x00
    SESSION_END = 0x01
    VERSION_MISMATCH = 0x02
    SERVER_SHUTDOWN = 0x03
    CLIENT_REQUEST = 0x04


class SessionType(IntEnum):
    """Session type codes used in DISCOVERY_ANNOUNCE and SESSION_UPDATE."""

    UNKNOWN = 0
    PRACTICE = 1
    QUALIFYING = 2
    RACE = 3
    TIME_ATTACK = 4


# ── Struct formats (all little-endian) ───────────────────────────────────────

# Discovery packet: fixed 176 bytes
_DISCOVERY_FMT = "<4sHB32s64s64sBHHI"
_DISCOVERY_SIZE = struct.calcsize(_DISCOVERY_FMT)  # 176

# Control message header: fixed 7 bytes followed by variable payload
_CTRL_HDR_FMT = "<4sHB"
_CTRL_HDR_SIZE = struct.calcsize(_CTRL_HDR_FMT)  # 7

# HELLO payload: client_name (32) + protocol_version (2)
_HELLO_FMT = "<32sH"
_HELLO_SIZE = struct.calcsize(_HELLO_FMT)

# WELCOME payload: session_id (4) + channel_count (2) — channel list appended
_WELCOME_HDR_FMT = "<IH"
_WELCOME_HDR_SIZE = struct.calcsize(_WELCOME_HDR_FMT)

# Per channel entry in WELCOME: channel_id (2) + name (32) + unit (16) + type (1) +
# min_val (8) + max_val (8)
_CHANNEL_ENTRY_FMT = "<H32s16sBdd"
_CHANNEL_ENTRY_SIZE = struct.calcsize(_CHANNEL_ENTRY_FMT)

# SUBSCRIBE (client → server): udp_port (2) + channel_count (2) + channel_ids (2 each)
# The udp_port tells the server which UDP port the client is listening on.
_SUBSCRIBE_HDR_FMT = "<HH"
_SUBSCRIBE_HDR_SIZE = struct.calcsize(_SUBSCRIBE_HDR_FMT)

# SUBSCRIBED (server → client): channel_count (2) + channel_ids (2 each)
_SUBSCRIBED_HDR_FMT = "<H"
_SUBSCRIBED_HDR_SIZE = struct.calcsize(_SUBSCRIBED_HDR_FMT)

# SESSION_UPDATE: track (64) + vehicle (64) + session_type (1)
_SESSION_UPDATE_FMT = "<64s64sB"
_SESSION_UPDATE_SIZE = struct.calcsize(_SESSION_UPDATE_FMT)

# PING / PONG: timestamp (8)
_PING_FMT = "<d"
_PING_SIZE = struct.calcsize(_PING_FMT)

# DISCONNECT: reason (1)
_DISCONNECT_FMT = "<B"
_DISCONNECT_SIZE = struct.calcsize(_DISCONNECT_FMT)

# Telemetry UDP frame header: magic (4) + session_id (4) + sequence (4) +
# timestamp (8) + channel_count (2) + lz4_compressed (1) = 23 bytes total
_TELEM_HDR_FMT = "<4sIIdH?"
_TELEM_HDR_SIZE = struct.calcsize(_TELEM_HDR_FMT)

# Per channel value in telemetry: channel_id (2) + value (8)
_TELEM_CHANNEL_FMT = "<Hd"
_TELEM_CHANNEL_SIZE = struct.calcsize(_TELEM_CHANNEL_FMT)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ChannelInfo:
    """Metadata for one telemetry channel, exchanged during WELCOME."""

    channel_id: int
    name: str
    unit: str
    # 0=float64, 1=float32, 2=int32, 3=bool  (matches ChannelType in tmu_format)
    type_tag: int
    min_val: float = 0.0
    max_val: float = 0.0


@dataclass
class TelemetryFrame:
    """Decoded telemetry UDP frame."""

    session_id: int
    sequence: int
    timestamp: float  # mElapsedTime (seconds)
    channels: dict[int, float] = field(default_factory=dict)  # channel_id → value


# ── Helpers ──────────────────────────────────────────────────────────────────


def _encode_str(s: str, width: int) -> bytes:
    """Encode *s* as UTF-8, null-padded or truncated to *width* bytes."""
    b = s.encode("utf-8")[:width]
    return b.ljust(width, b"\x00")


def _decode_str(b: bytes) -> str:
    """Decode null-terminated UTF-8 bytes."""
    return b.rstrip(b"\x00").decode("utf-8", errors="replace")


# ── Discovery ────────────────────────────────────────────────────────────────


def encode_discovery(
    *,
    driver_name: str,
    track_name: str,
    vehicle_name: str,
    session_type: int = SessionType.UNKNOWN,
    tcp_port: int = CONTROL_PORT,
    udp_port: int = TELEMETRY_PORT,
    session_id: int = 0,
) -> bytes:
    """Build a DISCOVERY_ANNOUNCE UDP broadcast packet (176 bytes)."""
    return struct.pack(
        _DISCOVERY_FMT,
        STREAM_MAGIC,
        PROTOCOL_VERSION,
        MsgType.DISCOVERY_ANNOUNCE,
        _encode_str(driver_name, 32),
        _encode_str(track_name, 64),
        _encode_str(vehicle_name, 64),
        int(session_type),
        tcp_port,
        udp_port,
        session_id,
    )


def decode_discovery(data: bytes) -> dict[str, Any]:
    """Decode a DISCOVERY_ANNOUNCE packet.

    Raises
    ------
    ValueError
        If the packet is too short, has the wrong magic, or is not a
        DISCOVERY_ANNOUNCE message.
    """
    if len(data) < _DISCOVERY_SIZE:
        raise ValueError(f"Discovery packet too short: {len(data)} < {_DISCOVERY_SIZE}")
    (
        magic,
        version,
        msg_type,
        driver_name_b,
        track_name_b,
        vehicle_name_b,
        session_type,
        tcp_port,
        udp_port,
        session_id,
    ) = struct.unpack_from(_DISCOVERY_FMT, data)
    _check_magic(magic)
    if msg_type != MsgType.DISCOVERY_ANNOUNCE:
        raise ValueError(f"Expected DISCOVERY_ANNOUNCE (0x01), got 0x{msg_type:02X}")
    return {
        "version": version,
        "driver_name": _decode_str(driver_name_b),
        "track_name": _decode_str(track_name_b),
        "vehicle_name": _decode_str(vehicle_name_b),
        "session_type": session_type,
        "tcp_port": tcp_port,
        "udp_port": udp_port,
        "session_id": session_id,
    }


# ── Control channel helpers ───────────────────────────────────────────────────


def _check_magic(magic: bytes) -> None:
    if magic != STREAM_MAGIC:
        raise ValueError(f"Invalid stream magic: {magic!r}")


def _encode_ctrl(msg_type: MsgType, payload: bytes) -> bytes:
    """Wrap *payload* in the standard control channel header."""
    header = struct.pack(_CTRL_HDR_FMT, STREAM_MAGIC, len(payload), int(msg_type))
    return header + payload


def _decode_ctrl_header(data: bytes) -> tuple[MsgType, bytes]:
    """Parse a control message from *data*.

    Returns ``(msg_type, payload_bytes)``.

    Raises
    ------
    ValueError
        If magic is wrong, data is too short, or declared length exceeds buffer.
    """
    if len(data) < _CTRL_HDR_SIZE:
        raise ValueError(f"Control header too short: {len(data)}")
    magic, length, msg_type_raw = struct.unpack_from(_CTRL_HDR_FMT, data)
    _check_magic(magic)
    end = _CTRL_HDR_SIZE + length
    if len(data) < end:
        raise ValueError(f"Control payload truncated: need {end}, have {len(data)}")
    return MsgType(msg_type_raw), data[_CTRL_HDR_SIZE:end]


# ── Handshake messages ───────────────────────────────────────────────────────


def encode_hello(client_name: str) -> bytes:
    """Encode a HELLO control message."""
    payload = struct.pack(_HELLO_FMT, _encode_str(client_name, 32), PROTOCOL_VERSION)
    return _encode_ctrl(MsgType.HELLO, payload)


def decode_hello(payload: bytes) -> dict[str, Any]:
    """Decode a HELLO payload."""
    if len(payload) < _HELLO_SIZE:
        raise ValueError("HELLO payload too short")
    name_b, version = struct.unpack_from(_HELLO_FMT, payload)
    return {"client_name": _decode_str(name_b), "protocol_version": version}


def encode_welcome(session_id: int, channels: list[ChannelInfo]) -> bytes:
    """Encode a WELCOME control message with the channel list."""
    header = struct.pack(_WELCOME_HDR_FMT, session_id, len(channels))
    entries = b"".join(
        struct.pack(
            _CHANNEL_ENTRY_FMT,
            ch.channel_id,
            _encode_str(ch.name, 32),
            _encode_str(ch.unit, 16),
            ch.type_tag,
            ch.min_val,
            ch.max_val,
        )
        for ch in channels
    )
    return _encode_ctrl(MsgType.WELCOME, header + entries)


def decode_welcome(payload: bytes) -> dict[str, Any]:
    """Decode a WELCOME payload."""
    if len(payload) < _WELCOME_HDR_SIZE:
        raise ValueError("WELCOME payload too short")
    session_id, channel_count = struct.unpack_from(_WELCOME_HDR_FMT, payload)
    channels: list[ChannelInfo] = []
    offset = _WELCOME_HDR_SIZE
    for _ in range(channel_count):
        if len(payload) < offset + _CHANNEL_ENTRY_SIZE:
            raise ValueError("WELCOME channel list truncated")
        ch_id, name_b, unit_b, type_tag, min_val, max_val = struct.unpack_from(
            _CHANNEL_ENTRY_FMT, payload, offset
        )
        channels.append(
            ChannelInfo(
                channel_id=ch_id,
                name=_decode_str(name_b),
                unit=_decode_str(unit_b),
                type_tag=type_tag,
                min_val=min_val,
                max_val=max_val,
            )
        )
        offset += _CHANNEL_ENTRY_SIZE
    return {"session_id": session_id, "channels": channels}


def encode_subscribe(channel_ids: list[int], *, udp_port: int = TELEMETRY_PORT) -> bytes:
    """Encode a SUBSCRIBE control message.

    Parameters
    ----------
    channel_ids:
        Channel IDs to subscribe to (empty = subscribe to all).
    udp_port:
        The local UDP port on which the client is listening for telemetry
        frames.  The server uses this to unicast UDP frames to the correct
        port on the client's machine.
    """
    header = struct.pack(_SUBSCRIBE_HDR_FMT, udp_port, len(channel_ids))
    ids = struct.pack(f"<{len(channel_ids)}H", *channel_ids) if channel_ids else b""
    return _encode_ctrl(MsgType.SUBSCRIBE, header + ids)


def decode_subscribe(payload: bytes) -> dict[str, Any]:
    """Decode a SUBSCRIBE payload (client → server).

    Returns a dict with keys ``udp_port`` and ``channel_ids``.
    """
    if len(payload) < _SUBSCRIBE_HDR_SIZE:
        raise ValueError("SUBSCRIBE payload too short")
    udp_port, count = struct.unpack_from(_SUBSCRIBE_HDR_FMT, payload)
    ids: list[int] = []
    if count:
        offset = _SUBSCRIBE_HDR_SIZE
        needed = offset + count * 2
        if len(payload) < needed:
            raise ValueError("SUBSCRIBE channel list truncated")
        ids = list(struct.unpack_from(f"<{count}H", payload, offset))
    return {"udp_port": udp_port, "channel_ids": ids}


def encode_subscribed(channel_ids: list[int]) -> bytes:
    """Encode a SUBSCRIBED control message (server → client)."""
    header = struct.pack(_SUBSCRIBED_HDR_FMT, len(channel_ids))
    ids = struct.pack(f"<{len(channel_ids)}H", *channel_ids) if channel_ids else b""
    return _encode_ctrl(MsgType.SUBSCRIBED, header + ids)


def decode_subscribed(payload: bytes) -> dict[str, Any]:
    """Decode a SUBSCRIBED payload (server → client).

    Returns a dict with key ``channel_ids``.
    """
    if len(payload) < _SUBSCRIBED_HDR_SIZE:
        raise ValueError("SUBSCRIBED payload too short")
    (count,) = struct.unpack_from(_SUBSCRIBED_HDR_FMT, payload)
    ids: list[int] = []
    if count:
        offset = _SUBSCRIBED_HDR_SIZE
        needed = offset + count * 2
        if len(payload) < needed:
            raise ValueError("SUBSCRIBED channel list truncated")
        ids = list(struct.unpack_from(f"<{count}H", payload, offset))
    return {"channel_ids": ids}


def encode_session_update(
    track: str, vehicle: str, session_type: int = SessionType.UNKNOWN
) -> bytes:
    """Encode a SESSION_UPDATE control message."""
    payload = struct.pack(
        _SESSION_UPDATE_FMT,
        _encode_str(track, 64),
        _encode_str(vehicle, 64),
        int(session_type),
    )
    return _encode_ctrl(MsgType.SESSION_UPDATE, payload)


def decode_session_update(payload: bytes) -> dict[str, Any]:
    """Decode a SESSION_UPDATE payload."""
    if len(payload) < _SESSION_UPDATE_SIZE:
        raise ValueError("SESSION_UPDATE payload too short")
    track_b, vehicle_b, session_type = struct.unpack_from(_SESSION_UPDATE_FMT, payload)
    return {
        "track": _decode_str(track_b),
        "vehicle": _decode_str(vehicle_b),
        "session_type": session_type,
    }


def encode_ping(timestamp: float) -> bytes:
    """Encode a PING keepalive message."""
    return _encode_ctrl(MsgType.PING, struct.pack(_PING_FMT, timestamp))


def encode_pong(timestamp: float) -> bytes:
    """Encode a PONG reply."""
    return _encode_ctrl(MsgType.PONG, struct.pack(_PING_FMT, timestamp))


def decode_ping_pong(payload: bytes) -> float:
    """Decode a PING or PONG payload, returning the echoed timestamp."""
    if len(payload) < _PING_SIZE:
        raise ValueError("PING/PONG payload too short")
    (ts,) = struct.unpack_from(_PING_FMT, payload)
    return ts


def encode_disconnect(reason: DisconnectReason = DisconnectReason.NORMAL) -> bytes:
    """Encode a DISCONNECT control message."""
    return _encode_ctrl(MsgType.DISCONNECT, struct.pack(_DISCONNECT_FMT, int(reason)))


def decode_disconnect(payload: bytes) -> dict[str, Any]:
    """Decode a DISCONNECT payload."""
    if len(payload) < _DISCONNECT_SIZE:
        raise ValueError("DISCONNECT payload too short")
    (reason,) = struct.unpack_from(_DISCONNECT_FMT, payload)
    return {"reason": reason}


# ── Telemetry frame (UDP) ─────────────────────────────────────────────────────


def encode_telemetry_frame(
    session_id: int,
    sequence: int,
    timestamp: float,
    channels: dict[int, float],
    *,
    compress: bool = True,
) -> bytes:
    """Encode a telemetry UDP datagram.

    Parameters
    ----------
    session_id:
        Unique session identifier (matches WELCOME session_id).
    sequence:
        Monotonically increasing sequence number (wraps at 2^32).
    timestamp:
        ``mElapsedTime`` in seconds.
    channels:
        Mapping of channel_id → float value.
    compress:
        When *True* (default) the channel data is LZ4-compressed.
        Set to *False* only for very small frames or testing.

    Raises
    ------
    ValueError
        If the resulting packet would exceed ``MAX_UDP_PAYLOAD``.
    """
    ch_count = len(channels)
    # Build channel payload: interleaved (channel_id uint16, value float64) pairs
    raw_channels = b"".join(
        struct.pack(_TELEM_CHANNEL_FMT, ch_id, value) for ch_id, value in channels.items()
    )

    if compress and raw_channels:
        payload = lz4.frame.compress(raw_channels, compression_level=0)
        compressed = True
    else:
        payload = raw_channels
        compressed = False

    header = struct.pack(
        _TELEM_HDR_FMT,
        STREAM_MAGIC,
        session_id,
        sequence,
        timestamp,
        ch_count,
        compressed,
    )
    packet = header + payload
    if len(packet) > MAX_UDP_PAYLOAD:
        raise ValueError(
            f"Telemetry packet too large ({len(packet)} bytes > {MAX_UDP_PAYLOAD}). "
            "Split channels across multiple frames."
        )
    return packet


def decode_telemetry_frame(data: bytes) -> TelemetryFrame:
    """Decode a telemetry UDP datagram.

    Raises
    ------
    ValueError
        If the packet is too short or has an invalid magic.
    """
    if len(data) < _TELEM_HDR_SIZE:
        raise ValueError(f"Telemetry packet too short: {len(data)}")
    magic, session_id, sequence, timestamp, ch_count, compressed = struct.unpack_from(
        _TELEM_HDR_FMT, data
    )
    _check_magic(magic)

    payload = data[_TELEM_HDR_SIZE:]
    if compressed:
        payload = lz4.frame.decompress(payload)

    expected = ch_count * _TELEM_CHANNEL_SIZE
    if len(payload) < expected:
        raise ValueError(
            f"Telemetry channel data truncated: need {expected}, have {len(payload)}"
        )

    channels: dict[int, float] = {}
    for i in range(ch_count):
        offset = i * _TELEM_CHANNEL_SIZE
        ch_id, value = struct.unpack_from(_TELEM_CHANNEL_FMT, payload, offset)
        channels[ch_id] = value

    return TelemetryFrame(
        session_id=session_id,
        sequence=sequence,
        timestamp=timestamp,
        channels=channels,
    )


# ── Canonical channel IDs ─────────────────────────────────────────────────────

#: Canonical channel-ID assignments.  Keep in sync with ``CHANNEL_NAMES``.
CHANNEL_ID = {
    "speed": 0,
    "rpm": 1,
    "throttle": 2,
    "brake": 3,
    "gear": 4,
    "steering": 5,
    "fuel": 6,
    "fuel_capacity": 7,
    "rpm_max": 8,
    "tyre_fl": 9,
    "tyre_fr": 10,
    "tyre_rl": 11,
    "tyre_rr": 12,
    "brake_temp_fl": 13,
    "brake_temp_fr": 14,
    "brake_temp_rl": 15,
    "brake_temp_rr": 16,
    "lap_dist": 17,
    "lap_time": 18,
    "pos_x": 19,
    "pos_y": 20,
    "pos_z": 21,
}

#: Reverse mapping: channel_id → name
CHANNEL_NAME: dict[int, str] = {v: k for k, v in CHANNEL_ID.items()}
