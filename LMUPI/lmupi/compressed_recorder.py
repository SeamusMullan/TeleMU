"""Real-time compressed telemetry recorder.

Streams telemetry frames into an LZ4-compressed file with chunk-based
compression for low latency and a chunk index table appended on finalize
to allow random access.

File layout
-----------
[Header]               fixed-size, identifies format + compressor
[Chunk 0]              compressed payload (N frames)
[Chunk 1]              …
  …
[Chunk K]
[Index Table]          array of (offset, compressed_size, frame_count) per chunk
[Footer]               index_table_offset, total_frames, total_chunks

Supported compressors: ``lz4`` (default), ``zstd`` (fallback).

Usage::

    rec = CompressedRecorder("session.tlm", chunk_frames=64)
    rec.start()
    for frame_bytes in telemetry_stream:
        rec.write_frame(frame_bytes)
    rec.finalize()
"""

from __future__ import annotations

import io
import logging
import struct
import time
from pathlib import Path
from typing import BinaryIO, Literal

import lz4.frame
import zstandard

logger = logging.getLogger(__name__)

# ── constants ──────────────────────────────────────────────────────────────
MAGIC = b"TLMU"
FORMAT_VERSION = 1
HEADER_SIZE = 16  # 4 magic + 4 version + 4 compressor_id + 4 reserved
INDEX_ENTRY_FMT = "<QII"  # offset(u64), compressed_size(u32), frame_count(u32)
INDEX_ENTRY_SIZE = struct.calcsize(INDEX_ENTRY_FMT)
FOOTER_FMT = "<QII"  # index_offset(u64), total_frames(u32), total_chunks(u32)
FOOTER_SIZE = struct.calcsize(FOOTER_FMT)

COMPRESSOR_LZ4 = 1
COMPRESSOR_ZSTD = 2

CompressorName = Literal["lz4", "zstd"]


# ── compressor helpers ─────────────────────────────────────────────────────

def _compress_lz4(data: bytes) -> bytes:
    return lz4.frame.compress(data)


def _decompress_lz4(data: bytes) -> bytes:
    return lz4.frame.decompress(data)


def _compress_zstd(data: bytes, *, level: int = 3) -> bytes:
    cctx = zstandard.ZstdCompressor(level=level)
    return cctx.compress(data)


def _decompress_zstd(data: bytes) -> bytes:
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data)


_COMPRESSORS = {
    "lz4": (COMPRESSOR_LZ4, _compress_lz4, _decompress_lz4),
    "zstd": (COMPRESSOR_ZSTD, _compress_zstd, _decompress_zstd),
}

_ID_TO_NAME = {COMPRESSOR_LZ4: "lz4", COMPRESSOR_ZSTD: "zstd"}


# ── recorder ───────────────────────────────────────────────────────────────

class CompressedRecorder:
    """Stream telemetry frames into a chunk-compressed file.

    Parameters
    ----------
    path:
        Destination file path.
    compressor:
        ``"lz4"`` (default) or ``"zstd"``.
    chunk_frames:
        Number of frames buffered before flushing a compressed chunk.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        compressor: CompressorName = "lz4",
        chunk_frames: int = 64,
    ) -> None:
        self._path = Path(path)
        if compressor not in _COMPRESSORS:
            raise ValueError(f"Unknown compressor: {compressor!r}")
        self._comp_id, self._compress, self._decompress = _COMPRESSORS[compressor]
        self._chunk_frames = max(1, chunk_frames)

        self._fp: BinaryIO | None = None
        self._frame_buf: list[bytes] = []
        self._index: list[tuple[int, int, int]] = []  # (offset, comp_size, n_frames)
        self._total_frames = 0
        self._started = False

    # ── lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Open the file and write the header."""
        if self._started:
            raise RuntimeError("Recorder already started")
        self._fp = open(self._path, "wb")
        self._write_header()
        self._started = True

    def finalize(self) -> None:
        """Flush remaining frames, write the index table & footer, close."""
        if not self._started:
            return
        self._flush_chunk()
        self._write_index_and_footer()
        self._fp.close()
        self._fp = None
        self._started = False
        logger.info(
            "Recording finalized: %d frames in %d chunks → %s",
            self._total_frames,
            len(self._index),
            self._path,
        )

    # ── writing ────────────────────────────────────────────────────────

    def write_frame(self, frame: bytes) -> None:
        """Buffer a single frame; flushes automatically when chunk is full."""
        if not self._started:
            raise RuntimeError("Recorder not started")
        self._frame_buf.append(frame)
        if len(self._frame_buf) >= self._chunk_frames:
            self._flush_chunk()

    # ── internals ──────────────────────────────────────────────────────

    def _write_header(self) -> None:
        hdr = struct.pack(
            "<4sIII",
            MAGIC,
            FORMAT_VERSION,
            self._comp_id,
            0,  # reserved
        )
        self._fp.write(hdr)

    def _flush_chunk(self) -> None:
        if not self._frame_buf:
            return
        # Concatenate frames with length-prefix for each
        buf = io.BytesIO()
        for f in self._frame_buf:
            buf.write(struct.pack("<I", len(f)))
            buf.write(f)
        raw = buf.getvalue()

        compressed = self._compress(raw)

        offset = self._fp.tell()
        # Write: compressed_size (u32) + compressed payload
        self._fp.write(struct.pack("<I", len(compressed)))
        self._fp.write(compressed)

        n = len(self._frame_buf)
        self._index.append((offset, len(compressed), n))
        self._total_frames += n
        self._frame_buf.clear()

    def _write_index_and_footer(self) -> None:
        index_offset = self._fp.tell()
        for entry in self._index:
            self._fp.write(struct.pack(INDEX_ENTRY_FMT, *entry))
        self._fp.write(
            struct.pack(FOOTER_FMT, index_offset, self._total_frames, len(self._index))
        )


# ── reader ─────────────────────────────────────────────────────────────────

class CompressedReader:
    """Read back a compressed telemetry recording.

    Supports random-access by chunk via the index table and sequential
    iteration over all frames.

    Parameters
    ----------
    path:
        Path to a ``.tlm`` file written by :class:`CompressedRecorder`.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._fp: BinaryIO | None = None
        self._comp_name: str = ""
        self._decompress = None
        self._index: list[tuple[int, int, int]] = []
        self._total_frames = 0
        self._total_chunks = 0

    def open(self) -> None:
        """Open the file and read header + index."""
        self._fp = open(self._path, "rb")
        self._read_header()
        self._read_index()

    def close(self) -> None:
        if self._fp:
            self._fp.close()
            self._fp = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    # ── public API ─────────────────────────────────────────────────────

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def total_chunks(self) -> int:
        return self._total_chunks

    @property
    def compressor(self) -> str:
        return self._comp_name

    def read_chunk(self, chunk_idx: int) -> list[bytes]:
        """Decompress and return all frames from *chunk_idx*."""
        if chunk_idx < 0 or chunk_idx >= self._total_chunks:
            raise IndexError(f"chunk index {chunk_idx} out of range")
        offset, comp_size, n_frames = self._index[chunk_idx]
        self._fp.seek(offset)
        raw_header = self._fp.read(4)
        stored_size = struct.unpack("<I", raw_header)[0]
        compressed = self._fp.read(stored_size)
        raw = self._decompress(compressed)
        return self._unpack_frames(raw, n_frames)

    def iter_frames(self):
        """Yield every frame in order."""
        for ci in range(self._total_chunks):
            yield from self.read_chunk(ci)

    # ── internals ──────────────────────────────────────────────────────

    def _read_header(self) -> None:
        hdr = self._fp.read(HEADER_SIZE)
        if len(hdr) < HEADER_SIZE:
            raise ValueError("Truncated file header")
        magic, version, comp_id, _ = struct.unpack("<4sIII", hdr)
        if magic != MAGIC:
            raise ValueError(f"Bad magic: {magic!r}")
        if version != FORMAT_VERSION:
            raise ValueError(f"Unsupported version: {version}")
        name = _ID_TO_NAME.get(comp_id)
        if name is None:
            raise ValueError(f"Unknown compressor id: {comp_id}")
        self._comp_name = name
        _, _, self._decompress = _COMPRESSORS[name]

    def _read_index(self) -> None:
        # Footer is at the very end
        self._fp.seek(-FOOTER_SIZE, 2)
        footer = self._fp.read(FOOTER_SIZE)
        index_offset, self._total_frames, self._total_chunks = struct.unpack(
            FOOTER_FMT, footer
        )
        self._fp.seek(index_offset)
        self._index = []
        for _ in range(self._total_chunks):
            entry = self._fp.read(INDEX_ENTRY_SIZE)
            self._index.append(struct.unpack(INDEX_ENTRY_FMT, entry))

    @staticmethod
    def _unpack_frames(raw: bytes, expected: int) -> list[bytes]:
        frames: list[bytes] = []
        pos = 0
        while pos < len(raw) and len(frames) < expected:
            (flen,) = struct.unpack_from("<I", raw, pos)
            pos += 4
            frames.append(raw[pos : pos + flen])
            pos += flen
        return frames
