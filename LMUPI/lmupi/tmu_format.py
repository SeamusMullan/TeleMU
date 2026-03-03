""".tmu binary file format definitions.

Defines the TeleMU binary file format for recording telemetry sessions.

File layout:
    [Header]              — magic, version, metadata offsets
    [Session metadata]    — JSON block with track, car, driver, date, sample rate
    [Channel table]       — list of (name, type_code, unit, byte_offset) entries
    [Compressed frames…]  — LZ4-compressed chunks, each containing N frames
    [Chunk index table]   — offsets and sizes for each compressed chunk
    [Footer]              — total frames, index table offset, checksum
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from enum import IntEnum

# ── Constants ─────────────────────────────────────────────

TMU_MAGIC = b"TMU\x00"  # 4-byte magic
TMU_VERSION = 1

# Type codes for channel data
class ChannelType(IntEnum):
    FLOAT64 = 0  # 8-byte double
    FLOAT32 = 1  # 4-byte float
    INT32 = 2    # 4-byte signed int
    INT16 = 3    # 2-byte signed int
    UINT8 = 4    # 1-byte unsigned int
    BOOL = 5     # 1-byte boolean


# struct format characters for each type code
CHANNEL_STRUCT_FMT = {
    ChannelType.FLOAT64: "d",
    ChannelType.FLOAT32: "f",
    ChannelType.INT32: "i",
    ChannelType.INT16: "h",
    ChannelType.UINT8: "B",
    ChannelType.BOOL: "?",
}

CHANNEL_TYPE_SIZE = {
    ChannelType.FLOAT64: 8,
    ChannelType.FLOAT32: 4,
    ChannelType.INT32: 4,
    ChannelType.INT16: 2,
    ChannelType.UINT8: 1,
    ChannelType.BOOL: 1,
}


# ── Data classes ──────────────────────────────────────────

@dataclass
class ChannelDef:
    """Definition of a single telemetry channel."""
    name: str
    type_code: ChannelType
    unit: str
    byte_offset: int = 0  # offset within a frame (computed at write time)


@dataclass
class SessionMetadata:
    """Session-level metadata stored as JSON in the file."""
    track: str = ""
    car: str = ""
    driver: str = ""
    date: str = ""
    sample_rate: int = 60
    extra: dict = field(default_factory=dict)

    def to_json_bytes(self) -> bytes:
        d = {
            "track": self.track,
            "car": self.car,
            "driver": self.driver,
            "date": self.date,
            "sample_rate": self.sample_rate,
        }
        d.update(self.extra)
        return json.dumps(d, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_json_bytes(cls, data: bytes) -> SessionMetadata:
        d = json.loads(data.decode("utf-8"))
        return cls(
            track=d.get("track", ""),
            car=d.get("car", ""),
            driver=d.get("driver", ""),
            date=d.get("date", ""),
            sample_rate=d.get("sample_rate", 60),
            extra={k: v for k, v in d.items()
                   if k not in ("track", "car", "driver", "date", "sample_rate")},
        )


@dataclass
class ChunkIndex:
    """Index entry for a compressed chunk."""
    file_offset: int      # byte offset in file
    compressed_size: int   # compressed size in bytes
    frame_count: int       # number of frames in this chunk
    first_frame_idx: int   # index of first frame in chunk


# ── Header ────────────────────────────────────────────────
# Layout (40 bytes):
#   4B  magic ("TMU\0")
#   2B  version (uint16)
#   2B  num_channels (uint16)
#   4B  sample_rate (uint32)
#   4B  metadata_offset (uint32)
#   4B  metadata_size (uint32)
#   4B  channel_table_offset (uint32)
#   4B  channel_table_size (uint32)
#   4B  data_start_offset (uint32)
#   8B  reserved

HEADER_FMT = "<4sHHIIIIIIQ"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# ── Footer ────────────────────────────────────────────────
# Layout (24 bytes):
#   8B  total_frames (uint64)
#   8B  index_table_offset (uint64)
#   4B  index_entry_count (uint32)
#   4B  magic (TMU\0) — repeated for validation

FOOTER_FMT = "<QQI4s"
FOOTER_SIZE = struct.calcsize(FOOTER_FMT)

# ── Channel table entry ──────────────────────────────────
# Layout (per entry):
#   1B  name_length (uint8)
#   NB  name (utf-8)
#   1B  type_code (uint8)
#   1B  unit_length (uint8)
#   NB  unit (utf-8)
#   4B  byte_offset (uint32)

# ── Chunk index entry ────────────────────────────────────
# 24 bytes per entry
CHUNK_INDEX_FMT = "<QIII"
CHUNK_INDEX_SIZE = struct.calcsize(CHUNK_INDEX_FMT)


def encode_header(
    num_channels: int,
    sample_rate: int,
    metadata_offset: int,
    metadata_size: int,
    channel_table_offset: int,
    channel_table_size: int,
    data_start_offset: int,
) -> bytes:
    return struct.pack(
        HEADER_FMT,
        TMU_MAGIC,
        TMU_VERSION,
        num_channels,
        sample_rate,
        metadata_offset,
        metadata_size,
        channel_table_offset,
        channel_table_size,
        data_start_offset,
        0,  # reserved
    )


def decode_header(data: bytes) -> dict:
    (magic, version, num_channels, sample_rate,
     metadata_offset, metadata_size,
     channel_table_offset, channel_table_size,
     data_start_offset, _reserved) = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    if magic != TMU_MAGIC:
        raise ValueError(f"Invalid TMU magic: {magic!r}")
    return {
        "version": version,
        "num_channels": num_channels,
        "sample_rate": sample_rate,
        "metadata_offset": metadata_offset,
        "metadata_size": metadata_size,
        "channel_table_offset": channel_table_offset,
        "channel_table_size": channel_table_size,
        "data_start_offset": data_start_offset,
    }


def encode_channel_table(channels: list[ChannelDef]) -> bytes:
    parts: list[bytes] = []
    for ch in channels:
        name_bytes = ch.name.encode("utf-8")
        unit_bytes = ch.unit.encode("utf-8")
        parts.append(struct.pack("B", len(name_bytes)))
        parts.append(name_bytes)
        parts.append(struct.pack("B", ch.type_code))
        parts.append(struct.pack("B", len(unit_bytes)))
        parts.append(unit_bytes)
        parts.append(struct.pack("<I", ch.byte_offset))
    return b"".join(parts)


def decode_channel_table(data: bytes, num_channels: int) -> list[ChannelDef]:
    channels: list[ChannelDef] = []
    offset = 0
    for _ in range(num_channels):
        name_len = data[offset]
        offset += 1
        name = data[offset:offset + name_len].decode("utf-8")
        offset += name_len
        type_code = ChannelType(data[offset])
        offset += 1
        unit_len = data[offset]
        offset += 1
        unit = data[offset:offset + unit_len].decode("utf-8")
        offset += unit_len
        byte_offset = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        channels.append(ChannelDef(
            name=name, type_code=type_code, unit=unit, byte_offset=byte_offset,
        ))
    return channels


def encode_footer(total_frames: int, index_table_offset: int, index_entry_count: int) -> bytes:
    return struct.pack(FOOTER_FMT, total_frames, index_table_offset, index_entry_count, TMU_MAGIC)


def decode_footer(data: bytes) -> dict:
    total_frames, index_table_offset, index_entry_count, magic = struct.unpack(FOOTER_FMT, data[-FOOTER_SIZE:])
    if magic != TMU_MAGIC:
        raise ValueError(f"Invalid TMU footer magic: {magic!r}")
    return {
        "total_frames": total_frames,
        "index_table_offset": index_table_offset,
        "index_entry_count": index_entry_count,
    }


def encode_chunk_index(entry: ChunkIndex) -> bytes:
    return struct.pack(CHUNK_INDEX_FMT, entry.file_offset, entry.compressed_size,
                       entry.frame_count, entry.first_frame_idx)


def decode_chunk_index(data: bytes) -> ChunkIndex:
    file_offset, compressed_size, frame_count, first_frame_idx = struct.unpack(CHUNK_INDEX_FMT, data)
    return ChunkIndex(file_offset=file_offset, compressed_size=compressed_size,
                      frame_count=frame_count, first_frame_idx=first_frame_idx)
