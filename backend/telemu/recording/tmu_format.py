""".tmu file format — binary telemetry recording format."""

Format layout:
    4 bytes  : magic  b"TMU\\x01"
    4 bytes  : header length (uint32 little-endian)
    N bytes  : JSON header (session metadata)
    remainder: zstd-compressed payload of newline-delimited JSON frames

Each frame line:
    {"ts": <float>, "channels": {<name>: <float>, ...}}

Lap-marker frames additionally carry:
    {"ts": ..., "channels": {...}, "lap_marker": {
        "lap": <int>, "last_time": <str>, "best_time": <str>,
        "sectors": [<str>, ...]
    }}
"""
TeleMU binary file format (.tmu) — reference implementation.

All multi-byte values are **little-endian**.
See docs/docs/recording/format-spec.md for the full specification.

Integrity verification:
- CRC-32 of all bytes before the footer (stored in footer)
- ``verify_tmu()`` checks CRC-32 and validates structure
- ``repair_tmu()`` copies valid frames, skipping corrupted data
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator

import zstandard as zstd

MAGIC = b"TMU\x01"
HEADER_LEN_FMT = "<I"  # uint32 LE


@dataclass
class TmuHeader:
    """Session metadata stored at the start of a .tmu file."""

    track: str = ""
    session_type: str = ""
    driver: str = ""
    vehicle: str = ""
    date: str = ""
    channels: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "track": self.track,
            "session_type": self.session_type,
            "driver": self.driver,
            "vehicle": self.vehicle,
            "date": self.date,
            "channels": self.channels,
        }
        d.update(self.extra)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TmuHeader:
        known = {"track", "session_type", "driver", "vehicle", "date", "channels"}
        extra = {k: v for k, v in d.items() if k not in known}
        return cls(
            track=d.get("track", ""),
            session_type=d.get("session_type", ""),
            driver=d.get("driver", ""),
            vehicle=d.get("vehicle", ""),
            date=d.get("date", ""),
            channels=d.get("channels", []),
            extra=extra,
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
class TmuFrame:
    """One telemetry sample."""

    ts: float
    channels: dict[str, float]
    lap_marker: dict[str, Any] | None = None


def read_tmu(path: Path | str) -> tuple[TmuHeader, list[TmuFrame]]:
    """Read a .tmu file and return (header, frames)."""
    header, frames = None, []
    for item in iter_tmu(path):
        if isinstance(item, TmuHeader):
            header = item
        else:
            frames.append(item)
    if header is None:
        header = TmuHeader()
    return header, frames


def iter_tmu(path: Path | str) -> Generator[TmuHeader | TmuFrame, None, None]:
    """Lazily iterate over a .tmu file yielding the header then frames."""
    path = Path(path)
    with open(path, "rb") as fh:
        magic = fh.read(4)
        if magic != MAGIC:
            raise ValueError(f"Not a .tmu file (bad magic: {magic!r})")

        hdr_len_bytes = fh.read(4)
        if len(hdr_len_bytes) < 4:
            raise ValueError("Truncated .tmu header length")
        (hdr_len,) = struct.unpack(HEADER_LEN_FMT, hdr_len_bytes)

        hdr_json = fh.read(hdr_len)
        if len(hdr_json) < hdr_len:
            raise ValueError("Truncated .tmu header")

        header = TmuHeader.from_dict(json.loads(hdr_json))
        yield header

        compressed = fh.read()

    if not compressed:
        return

    dctx = zstd.ZstdDecompressor()
    payload = dctx.decompress(compressed)

    for line in payload.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        yield TmuFrame(
            ts=obj["ts"],
            channels=obj.get("channels", {}),
            lap_marker=obj.get("lap_marker"),
        )


def write_tmu(
    path: Path | str,
    header: TmuHeader,
    frames: list[TmuFrame],
    compression_level: int = 3,
) -> None:
    """Write a .tmu file."""
    path = Path(path)
    hdr_bytes = json.dumps(header.to_dict(), separators=(",", ":")).encode()

    lines: list[bytes] = []
    for f in frames:
        obj: dict[str, Any] = {"ts": f.ts, "channels": f.channels}
        if f.lap_marker:
            obj["lap_marker"] = f.lap_marker
        lines.append(json.dumps(obj, separators=(",", ":")).encode())
    payload = b"\n".join(lines)

    cctx = zstd.ZstdCompressor(level=compression_level)
    compressed = cctx.compress(payload)

    with open(path, "wb") as fh:
        fh.write(MAGIC)
        fh.write(struct.pack(HEADER_LEN_FMT, len(hdr_bytes)))
        fh.write(hdr_bytes)
        fh.write(compressed)
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


# ── Integrity verification ────────────────────────────────────────────────────


class TMUCorruptionError(Exception):
    """Raised when a .tmu file fails integrity checks."""


@dataclass
class VerifyResult:
    """Result of a verification pass."""

    ok: bool = True
    crc32_ok: bool = True
    header_ok: bool = True
    frame_count: int = 0
    message: str = ""


def verify_tmu(data: bytes) -> VerifyResult:
    """Verify integrity of a .tmu byte string.

    Checks:
    1. Magic bytes and header parsing.
    2. CRC-32 of all bytes before the footer matches the footer checksum.
    3. Frame index offsets are within bounds.
    """
    result = VerifyResult()

    if len(data) < HEADER_FIXED_SIZE + FOOTER_SIZE:
        return VerifyResult(ok=False, header_ok=False, message="File too small")

    # -- header --
    magic = data[:4]
    if magic != MAGIC:
        return VerifyResult(ok=False, header_ok=False, message=f"Bad magic: {magic!r}")

    try:
        TMUHeader.unpack(data)
    except ValueError as exc:
        return VerifyResult(ok=False, header_ok=False, message=f"Header error: {exc}")

    # -- footer --
    try:
        footer = TMUFooter.unpack(data[-FOOTER_SIZE:])
    except ValueError as exc:
        return VerifyResult(ok=False, message=f"Footer error: {exc}")

    result.frame_count = footer.frame_count

    # -- CRC-32 --
    body = data[:-FOOTER_SIZE]
    computed_crc = zlib.crc32(body) & 0xFFFFFFFF
    if computed_crc != footer.checksum:
        result.crc32_ok = False
        result.ok = False

    # -- frame index bounds check --
    hdr = TMUHeader.unpack(data)
    meta_end = HEADER_FIXED_SIZE + len(hdr.metadata_json)
    channels: list[ChannelDef] = []
    for i in range(hdr.channel_count):
        offset = meta_end + i * CHANNEL_DEF_SIZE
        channels.append(ChannelDef.unpack(data[offset : offset + CHANNEL_DEF_SIZE]))
    fsize = frame_payload_size(channels) if channels else 0

    for i in range(footer.frame_count):
        idx_pos = footer.index_offset + i * 8
        if idx_pos + 8 > len(data) - FOOTER_SIZE:
            result.ok = False
            result.message = f"Frame index entry {i} out of bounds"
            return result
        (frame_offset,) = struct.unpack("<Q", data[idx_pos : idx_pos + 8])
        if fsize > 0 and frame_offset + fsize > footer.index_offset:
            result.ok = False
            result.message = f"Frame {i} at offset {frame_offset} overlaps index"
            return result

    if result.ok:
        result.message = f"OK — {result.frame_count} frames verified"
    else:
        parts: list[str] = []
        if not result.crc32_ok:
            parts.append("CRC-32 mismatch")
        if not result.header_ok:
            parts.append("Header invalid")
        result.message = "; ".join(parts)

    return result


def verify_file(path) -> VerifyResult:
    """Verify integrity of a .tmu file on disk."""
    from pathlib import Path

    data = Path(path).read_bytes()
    return verify_tmu(data)


def repair_tmu(
    data: bytes,
    *,
    header_override: TMUHeader | None = None,
    channels_override: list[ChannelDef] | None = None,
) -> tuple[bytes, int, int]:
    """Attempt to recover valid frames from a possibly-corrupted .tmu byte string.

    Returns ``(repaired_data, recovered_count, skipped_count)``.
    """
    if len(data) < HEADER_FIXED_SIZE + FOOTER_SIZE:
        raise TMUCorruptionError("File too small to repair")

    # Parse what we can from the header
    try:
        hdr = header_override or TMUHeader.unpack(data)
    except ValueError as exc:
        raise TMUCorruptionError(f"Cannot parse header: {exc}") from exc

    # Parse channel defs
    meta_end = HEADER_FIXED_SIZE + len(hdr.metadata_json)
    if channels_override is not None:
        channels = channels_override
    else:
        channels = []
        for i in range(hdr.channel_count):
            offset = meta_end + i * CHANNEL_DEF_SIZE
            try:
                channels.append(ChannelDef.unpack(data[offset : offset + CHANNEL_DEF_SIZE]))
            except (ValueError, struct.error):
                break

    if not channels:
        raise TMUCorruptionError("No channel definitions found")

    fsize = frame_payload_size(channels)

    # Parse footer (best effort)
    try:
        footer = TMUFooter.unpack(data[-FOOTER_SIZE:])
    except ValueError:
        footer = None

    # Collect valid frames
    valid_frames: list[tuple[float, list[tuple[ChannelType, object]]]] = []
    skipped = 0

    if footer is not None:
        # Try to read frames via the index
        for i in range(footer.frame_count):
            idx_pos = footer.index_offset + i * 8
            if idx_pos + 8 > len(data):
                skipped += 1
                continue
            (frame_offset,) = struct.unpack("<Q", data[idx_pos : idx_pos + 8])
            if frame_offset + fsize > len(data):
                skipped += 1
                continue
            frame_data = data[frame_offset : frame_offset + fsize]
            try:
                ts, vals = unpack_frame(frame_data, channels)
                channel_values = [
                    (ch.channel_type, vals[ch.name]) for ch in channels
                ]
                valid_frames.append((ts, channel_values))
            except (struct.error, KeyError, ValueError):
                skipped += 1

    recovered = len(valid_frames)

    # Rebuild a clean file
    repaired = build_minimal_tmu(
        track=hdr.track_name,
        vehicle=hdr.vehicle_name,
        driver=hdr.driver_name,
        channels=channels,
        frames=valid_frames if valid_frames else None,
        metadata=json.loads(hdr.metadata_json) if hdr.metadata_json else None,
    )

    return repaired, recovered, skipped


def repair_file(src, dst) -> tuple[int, int]:
    """Repair a corrupted .tmu file, writing valid frames to *dst*.

    Returns ``(recovered, skipped)`` frame counts.
    """
    from pathlib import Path

    data = Path(src).read_bytes()
    repaired, recovered, skipped = repair_tmu(data)
    Path(dst).write_bytes(repaired)
    return recovered, skipped
