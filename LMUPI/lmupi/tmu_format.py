"""
TeleMU binary file format (.tmu) – reference implementation.

See docs/docs/architecture/tmu-format.md for the full specification.
"""

from __future__ import annotations

import enum
import json
import struct
from dataclasses import dataclass, field
from typing import Any, BinaryIO

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TMU_MAGIC: bytes = b"TMU\x1a"
FORMAT_VERSION: int = 0x0100  # v1.0

# struct formats (little-endian)
HEADER_FORMAT: str = "<4sHHHHIQ8s"
HEADER_SIZE: int = struct.calcsize(HEADER_FORMAT)  # 32

CHANNEL_FORMAT: str = "<32sB8s7s"
CHANNEL_SIZE: int = struct.calcsize(CHANNEL_FORMAT)  # 48


# ---------------------------------------------------------------------------
# Data-type enum
# ---------------------------------------------------------------------------


class ChannelDtype(enum.IntEnum):
    """Data type identifiers stored in each channel definition."""

    FLOAT64 = 0
    FLOAT32 = 1
    INT32 = 2
    INT16 = 3
    UINT8 = 4
    BOOL = 5


DTYPE_STRUCT: dict[ChannelDtype, str] = {
    ChannelDtype.FLOAT64: "<d",
    ChannelDtype.FLOAT32: "<f",
    ChannelDtype.INT32: "<i",
    ChannelDtype.INT16: "<h",
    ChannelDtype.UINT8: "<B",
    ChannelDtype.BOOL: "<?",
}

DTYPE_SIZE: dict[ChannelDtype, int] = {
    dt: struct.calcsize(fmt) for dt, fmt in DTYPE_STRUCT.items()
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ChannelDef:
    """A single channel definition."""

    name: str
    dtype: ChannelDtype
    unit: str = ""

    def pack(self) -> bytes:
        """Serialise to 48 bytes."""
        return struct.pack(
            CHANNEL_FORMAT,
            self.name.encode("utf-8").ljust(32, b"\x00")[:32],
            int(self.dtype),
            self.unit.encode("utf-8").ljust(8, b"\x00")[:8],
            b"\x00" * 7,
        )

    @classmethod
    def unpack(cls, data: bytes) -> ChannelDef:
        """Deserialise from 48 bytes."""
        raw_name, dtype_val, raw_unit, _ = struct.unpack(CHANNEL_FORMAT, data)
        return cls(
            name=raw_name.rstrip(b"\x00").decode("utf-8"),
            dtype=ChannelDtype(dtype_val),
            unit=raw_unit.rstrip(b"\x00").decode("utf-8"),
        )


@dataclass
class TMUHeader:
    """File header (32 bytes)."""

    version: int = FORMAT_VERSION
    flags: int = 0
    channel_count: int = 0
    sample_rate_hz: int = 60
    metadata_length: int = 0
    frame_count: int = 0

    def pack(self) -> bytes:
        return struct.pack(
            HEADER_FORMAT,
            TMU_MAGIC,
            self.version,
            self.flags,
            self.channel_count,
            self.sample_rate_hz,
            self.metadata_length,
            self.frame_count,
            b"\x00" * 8,
        )

    @classmethod
    def unpack(cls, data: bytes) -> TMUHeader:
        (
            magic,
            version,
            flags,
            channel_count,
            sample_rate_hz,
            metadata_length,
            frame_count,
            _reserved,
        ) = struct.unpack(HEADER_FORMAT, data)
        if magic != TMU_MAGIC:
            raise ValueError(f"Invalid TMU magic bytes: {magic!r}")
        return cls(
            version=version,
            flags=flags,
            channel_count=channel_count,
            sample_rate_hz=sample_rate_hz,
            metadata_length=metadata_length,
            frame_count=frame_count,
        )


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


@dataclass
class TMUWriter:
    """Sequential writer for .tmu files."""

    _fp: BinaryIO | None = None
    _channels: list[ChannelDef] = field(default_factory=list)
    _frame_format: str = ""
    _frame_count: int = 0
    _header_written: bool = False

    def begin(
        self,
        fp: BinaryIO,
        channels: list[ChannelDef],
        metadata: dict[str, Any],
        sample_rate_hz: int = 60,
    ) -> None:
        """Write the header, metadata, and channel table."""
        self._fp = fp
        self._channels = list(channels)
        self._frame_count = 0

        meta_bytes = json.dumps(metadata, separators=(",", ":")).encode("utf-8")

        header = TMUHeader(
            channel_count=len(channels),
            sample_rate_hz=sample_rate_hz,
            metadata_length=len(meta_bytes),
            frame_count=0,
        )
        fp.write(header.pack())
        fp.write(meta_bytes)
        for ch in channels:
            fp.write(ch.pack())

        # Pre-compute the struct format for a single frame
        parts = ["d"]  # timestamp
        for ch in channels:
            parts.append(DTYPE_STRUCT[ch.dtype].lstrip("<"))
        self._frame_format = "<" + "".join(parts)
        self._header_written = True

    def write_frame(self, timestamp: float, values: list[Any]) -> None:
        """Append a single frame."""
        assert self._fp is not None
        self._fp.write(struct.pack(self._frame_format, timestamp, *values))
        self._frame_count += 1

    def finish(self) -> None:
        """Update the frame count in the header and flush."""
        assert self._fp is not None
        self._fp.seek(16)  # offset of frame_count in header
        self._fp.write(struct.pack("<Q", self._frame_count))
        self._fp.flush()


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


@dataclass
class TMUReader:
    """Streaming reader for .tmu files."""

    header: TMUHeader = field(default_factory=TMUHeader)
    metadata: dict[str, Any] = field(default_factory=dict)
    channels: list[ChannelDef] = field(default_factory=list)
    _fp: BinaryIO | None = None
    _frame_format: str = ""
    _frame_size: int = 0

    def open(self, fp: BinaryIO) -> None:
        """Read header, metadata, and channel definitions."""
        self._fp = fp

        raw_header = fp.read(HEADER_SIZE)
        if len(raw_header) < HEADER_SIZE:
            raise ValueError("File too short for TMU header")
        self.header = TMUHeader.unpack(raw_header)

        raw_meta = fp.read(self.header.metadata_length)
        self.metadata = json.loads(raw_meta.decode("utf-8"))

        self.channels = []
        for _ in range(self.header.channel_count):
            raw_ch = fp.read(CHANNEL_SIZE)
            self.channels.append(ChannelDef.unpack(raw_ch))

        parts = ["d"]
        for ch in self.channels:
            parts.append(DTYPE_STRUCT[ch.dtype].lstrip("<"))
        self._frame_format = "<" + "".join(parts)
        self._frame_size = struct.calcsize(self._frame_format)

    def read_frame(self) -> tuple[float, list[Any]] | None:
        """Read the next frame.  Returns ``None`` at EOF."""
        assert self._fp is not None
        raw = self._fp.read(self._frame_size)
        if len(raw) < self._frame_size:
            return None
        values = struct.unpack(self._frame_format, raw)
        return values[0], list(values[1:])

    def read_all_frames(self) -> list[tuple[float, list[Any]]]:
        """Read every remaining frame into a list."""
        frames: list[tuple[float, list[Any]]] = []
        while True:
            frame = self.read_frame()
            if frame is None:
                break
            frames.append(frame)
        return frames
