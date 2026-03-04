"""
TeleMU binary file format (.tmu) — reference implementation.

All multi-byte values are **little-endian**.
See docs/docs/recording/format-spec.md for the full specification.
"""

from __future__ import annotations

import json
import struct
import time
import zlib
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Self

# ── Constants ─────────────────────────────────────────────────────────────────

MAGIC = b"TMU\x01"
FORMAT_VERSION: int = 1

# Fixed sizes
HEADER_FIXED_SIZE = 4 + 2 + 8 + 64 + 64 + 32 + 1 + 2 + 2 + 4  # 183 bytes
CHANNEL_DEF_SIZE = 32 + 1 + 16 + 2  # 51 bytes
FRAME_HEADER_SIZE = 8  # timestamp only (float64)
FOOTER_SIZE = 8 + 8 + 4  # frame_count + index_offset + checksum = 20 bytes

# struct format strings (little-endian)
HEADER_FMT = "<4sHd64s64s32sBHHI"
CHANNEL_DEF_FMT = "<32sB16sH"
FRAME_HEADER_FMT = "<d"
FOOTER_FMT = "<QQI"


# ── Enumerations ──────────────────────────────────────────────────────────────


class ChannelType(IntEnum):
    """Data type tag stored in each channel definition."""

    FLOAT64 = 0
    FLOAT32 = 1
    INT32 = 2
    UINT16 = 3
    BOOL = 4

    @property
    def size(self) -> int:
        """Byte width of one value of this type."""
        return _CHANNEL_TYPE_SIZES[self]

    @property
    def struct_char(self) -> str:
        """``struct`` format character (little-endian implied)."""
        return _CHANNEL_TYPE_STRUCT[self]


_CHANNEL_TYPE_SIZES: dict[ChannelType, int] = {
    ChannelType.FLOAT64: 8,
    ChannelType.FLOAT32: 4,
    ChannelType.INT32: 4,
    ChannelType.UINT16: 2,
    ChannelType.BOOL: 1,
}

_CHANNEL_TYPE_STRUCT: dict[ChannelType, str] = {
    ChannelType.FLOAT64: "d",
    ChannelType.FLOAT32: "f",
    ChannelType.INT32: "i",
    ChannelType.UINT16: "H",
    ChannelType.BOOL: "?",
}


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ChannelDef:
    """One entry in the channel definition table."""

    name: str
    channel_type: ChannelType
    unit: str
    byte_offset: int  # offset within the frame *payload* (after timestamp)

    # ── serialisation ─────────────────────────────────────────────────────

    def pack(self) -> bytes:
        return struct.pack(
            CHANNEL_DEF_FMT,
            self.name.encode("utf-8").ljust(32, b"\x00")[:32],
            int(self.channel_type),
            self.unit.encode("utf-8").ljust(16, b"\x00")[:16],
            self.byte_offset,
        )

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        name_raw, ctype, unit_raw, offset = struct.unpack(CHANNEL_DEF_FMT, data)
        return cls(
            name=name_raw.rstrip(b"\x00").decode("utf-8"),
            channel_type=ChannelType(ctype),
            unit=unit_raw.rstrip(b"\x00").decode("utf-8"),
            byte_offset=offset,
        )


@dataclass
class TMUHeader:
    """Fixed-size file header followed by variable-length metadata JSON."""

    track_name: str
    vehicle_name: str
    driver_name: str
    session_type: int = 0
    sample_rate_hz: int = 60
    created_at: float = field(default_factory=time.time)
    metadata_json: bytes = b"{}"
    channel_count: int = 0
    version: int = FORMAT_VERSION

    # ── serialisation ─────────────────────────────────────────────────────

    def pack(self) -> bytes:
        """Serialise the header (fixed part + metadata blob)."""
        fixed = struct.pack(
            HEADER_FMT,
            MAGIC,
            self.version,
            self.created_at,
            self.track_name.encode("utf-8").ljust(64, b"\x00")[:64],
            self.vehicle_name.encode("utf-8").ljust(64, b"\x00")[:64],
            self.driver_name.encode("utf-8").ljust(32, b"\x00")[:32],
            self.session_type,
            self.sample_rate_hz,
            self.channel_count,
            len(self.metadata_json),
        )
        return fixed + self.metadata_json

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        """Deserialise the header from a bytes buffer.

        ``data`` must contain at least ``HEADER_FIXED_SIZE`` bytes.
        If the metadata length field is > 0 the buffer must also include those bytes.
        """
        if len(data) < HEADER_FIXED_SIZE:
            raise ValueError(
                f"Header data too short: {len(data)} < {HEADER_FIXED_SIZE}"
            )

        magic, version, created_at, track_raw, vehicle_raw, driver_raw, session_type, sample_rate_hz, channel_count, meta_len = (
            struct.unpack(HEADER_FMT, data[:HEADER_FIXED_SIZE])
        )

        if magic != MAGIC:
            raise ValueError(f"Bad magic bytes: {magic!r} (expected {MAGIC!r})")

        meta_end = HEADER_FIXED_SIZE + meta_len
        if len(data) < meta_end:
            raise ValueError(
                f"Metadata truncated: need {meta_end} bytes, got {len(data)}"
            )
        metadata_json = data[HEADER_FIXED_SIZE:meta_end]

        return cls(
            version=version,
            created_at=created_at,
            track_name=track_raw.rstrip(b"\x00").decode("utf-8"),
            vehicle_name=vehicle_raw.rstrip(b"\x00").decode("utf-8"),
            driver_name=driver_raw.rstrip(b"\x00").decode("utf-8"),
            session_type=session_type,
            sample_rate_hz=sample_rate_hz,
            channel_count=channel_count,
            metadata_json=metadata_json,
        )


@dataclass
class TMUFooter:
    """Written after all frames. Enables seeking and integrity checks."""

    frame_count: int
    index_offset: int
    checksum: int  # CRC-32

    def pack(self) -> bytes:
        return struct.pack(FOOTER_FMT, self.frame_count, self.index_offset, self.checksum)

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        if len(data) < FOOTER_SIZE:
            raise ValueError(f"Footer data too short: {len(data)} < {FOOTER_SIZE}")
        fc, io, cs = struct.unpack(FOOTER_FMT, data[:FOOTER_SIZE])
        return cls(frame_count=fc, index_offset=io, checksum=cs)


# ── Frame helpers ─────────────────────────────────────────────────────────────


def pack_frame(timestamp: float, channel_values: list[tuple[ChannelType, object]]) -> bytes:
    """Pack a single frame: ``float64`` timestamp followed by channel values.

    *channel_values* is a list of ``(ChannelType, value)`` pairs **in the same
    order** as the channel definition table.
    """
    parts: list[bytes] = [struct.pack(FRAME_HEADER_FMT, timestamp)]
    for ctype, value in channel_values:
        parts.append(struct.pack(f"<{ctype.struct_char}", value))
    return b"".join(parts)


def unpack_frame(
    data: bytes, channels: list[ChannelDef]
) -> tuple[float, dict[str, object]]:
    """Unpack a frame into ``(timestamp, {channel_name: value, ...})``."""
    (timestamp,) = struct.unpack(FRAME_HEADER_FMT, data[:FRAME_HEADER_SIZE])
    values: dict[str, object] = {}
    for ch in channels:
        offset = FRAME_HEADER_SIZE + ch.byte_offset
        size = ch.channel_type.size
        (val,) = struct.unpack(
            f"<{ch.channel_type.struct_char}", data[offset : offset + size]
        )
        values[ch.name] = val
    return timestamp, values


def compute_channel_offsets(channels: list[ChannelDef]) -> None:
    """Fill in ``byte_offset`` for each channel sequentially (no padding)."""
    offset = 0
    for ch in channels:
        ch.byte_offset = offset
        offset += ch.channel_type.size


def frame_payload_size(channels: list[ChannelDef]) -> int:
    """Total byte size of one frame (timestamp + all channel values)."""
    return FRAME_HEADER_SIZE + sum(ch.channel_type.size for ch in channels)


# ── Minimal file builder (for testing / examples) ────────────────────────────


def build_minimal_tmu(
    *,
    track: str = "Monza",
    vehicle: str = "Porsche 963",
    driver: str = "Player",
    channels: list[ChannelDef] | None = None,
    frames: list[tuple[float, list[tuple[ChannelType, object]]]] | None = None,
    metadata: dict | None = None,
) -> bytes:
    """Return a complete, valid ``.tmu`` byte string.

    Useful for tests and to produce the example hex dump in the spec.
    """
    if channels is None:
        channels = [
            ChannelDef("speed", ChannelType.FLOAT64, "km/h", 0),
            ChannelDef("rpm", ChannelType.FLOAT64, "rpm", 8),
            ChannelDef("gear", ChannelType.INT32, "", 16),
        ]
        compute_channel_offsets(channels)

    if frames is None:
        frames = [
            (0.0, [(ChannelType.FLOAT64, 0.0), (ChannelType.FLOAT64, 800.0), (ChannelType.INT32, 0)]),
            (0.016, [(ChannelType.FLOAT64, 42.5), (ChannelType.FLOAT64, 3500.0), (ChannelType.INT32, 1)]),
        ]

    meta_bytes = json.dumps(metadata or {}).encode("utf-8")

    header = TMUHeader(
        track_name=track,
        vehicle_name=vehicle,
        driver_name=driver,
        channel_count=len(channels),
        metadata_json=meta_bytes,
    )

    parts: list[bytes] = []
    parts.append(header.pack())

    # Channel definition table
    for ch in channels:
        parts.append(ch.pack())

    # Frame index placeholder offset (right after header + channel defs)
    data_offset = sum(len(p) for p in parts)

    # Pack frames and record offsets
    frame_offsets: list[int] = []
    frame_blobs: list[bytes] = []
    current_offset = data_offset
    for ts, vals in frames:
        raw = pack_frame(ts, vals)
        frame_offsets.append(current_offset)
        frame_blobs.append(raw)
        current_offset += len(raw)

    for blob in frame_blobs:
        parts.append(blob)

    # Frame index
    index_offset = sum(len(p) for p in parts)
    for off in frame_offsets:
        parts.append(struct.pack("<Q", off))

    # CRC-32 over everything before footer
    body = b"".join(parts)
    checksum = zlib.crc32(body) & 0xFFFFFFFF

    footer = TMUFooter(
        frame_count=len(frames),
        index_offset=index_offset,
        checksum=checksum,
    )
    parts.append(footer.pack())

    return b"".join(parts)
