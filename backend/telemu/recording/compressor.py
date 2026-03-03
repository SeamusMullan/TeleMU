"""Streaming compressor for real-time telemetry recording.

Provides chunk-based LZ4 frame compression with a seekable chunk index table,
targeting < 1ms latency per chunk at 60Hz.  Falls back to zstandard when requested.

File layout (`.tmu` file)
-------------------------
[compressed chunk 0][compressed chunk 1] … [compressed chunk N]
[chunk index table — JSON]
[8-byte little-endian uint64: byte offset where the index table starts]
[4-byte magic: b"TMU\\x01"]
"""

from __future__ import annotations

import io
import json
import struct
from typing import Literal

import lz4.frame
import zstandard as zstd

# 4-byte file-tail magic to identify TMU compressed files
MAGIC = b"TMU\x01"
MAGIC_LEN = len(MAGIC)
INDEX_OFFSET_LEN = 8  # uint64 little-endian


class StreamCompressor:
    """Chunk-based streaming compressor for telemetry data.

    Parameters
    ----------
    dest : str | io.RawIOBase
        File path or writable binary stream.
    chunk_frames : int
        Number of frames to buffer before compressing a chunk.
    algorithm : "lz4" | "zstd"
        Compression algorithm to use.
    """

    def __init__(
        self,
        dest: str | io.RawIOBase,
        chunk_frames: int = 60,
        algorithm: Literal["lz4", "zstd"] = "lz4",
    ) -> None:
        if isinstance(dest, (str,)):
            self._fp = open(dest, "wb")  # noqa: SIM115
            self._owns_fp = True
        else:
            self._fp = dest
            self._owns_fp = False

        self.algorithm = algorithm
        self.chunk_frames = chunk_frames

        # Chunk index: list of (offset, compressed_size, raw_size, frame_count)
        self._index: list[dict] = []
        self._buf = bytearray()
        self._buffered_frames = 0
        self._finalized = False

    # ── public API ────────────────────────────────────────────────────────

    def write_frame(self, data: bytes) -> None:
        """Buffer a single serialised frame; flush when chunk is full."""
        if self._finalized:
            raise RuntimeError("Cannot write to a finalised compressor")
        self._buf.extend(data)
        self._buffered_frames += 1
        if self._buffered_frames >= self.chunk_frames:
            self._flush_chunk()

    def finalize(self) -> None:
        """Flush remaining data and append the chunk index table + trailer."""
        if self._finalized:
            return
        # flush any remaining buffered data
        if self._buffered_frames > 0:
            self._flush_chunk()
        self._write_trailer()
        self._finalized = True
        if self._owns_fp:
            self._fp.close()

    @property
    def index(self) -> list[dict]:
        """Return a *copy* of the chunk index built so far."""
        return list(self._index)

    # ── internals ─────────────────────────────────────────────────────────

    def _compress(self, raw: bytes) -> bytes:
        if self.algorithm == "lz4":
            return lz4.frame.compress(raw)
        return zstd.ZstdCompressor().compress(raw)

    def _flush_chunk(self) -> None:
        raw = bytes(self._buf)
        compressed = self._compress(raw)
        offset = self._fp.tell()
        self._fp.write(compressed)
        self._index.append(
            {
                "offset": offset,
                "compressed_size": len(compressed),
                "raw_size": len(raw),
                "frame_count": self._buffered_frames,
            }
        )
        self._buf.clear()
        self._buffered_frames = 0

    def _write_trailer(self) -> None:
        index_offset = self._fp.tell()
        index_bytes = json.dumps(
            {"algorithm": self.algorithm, "chunks": self._index}
        ).encode()
        self._fp.write(index_bytes)
        self._fp.write(struct.pack("<Q", index_offset))
        self._fp.write(MAGIC)


# ── Reader helper ─────────────────────────────────────────────────────────────


def read_index(src: str | io.RawIOBase) -> dict:
    """Read the chunk index table from a TMU compressed file.

    Returns a dict with keys ``algorithm`` and ``chunks``.
    """
    if isinstance(src, (str,)):
        fp = open(src, "rb")  # noqa: SIM115
        owns = True
    else:
        fp = src
        owns = False
    try:
        # Read magic
        fp.seek(-(MAGIC_LEN + INDEX_OFFSET_LEN), 2)
        raw_offset = fp.read(INDEX_OFFSET_LEN)
        magic = fp.read(MAGIC_LEN)
        if magic != MAGIC:
            raise ValueError("Not a valid TMU compressed file")
        (index_offset,) = struct.unpack("<Q", raw_offset)
        fp.seek(index_offset)
        index_len = (
            fp.seek(0, 2) - index_offset - MAGIC_LEN - INDEX_OFFSET_LEN
        )
        fp.seek(index_offset)
        index_data = fp.read(index_len)
        return json.loads(index_data)
    finally:
        if owns:
            fp.close()


def decompress_chunk(
    src: str | io.RawIOBase,
    chunk_meta: dict,
    algorithm: str = "lz4",
) -> bytes:
    """Decompress a single chunk from a TMU file given its index metadata."""
    if isinstance(src, (str,)):
        fp = open(src, "rb")  # noqa: SIM115
        owns = True
    else:
        fp = src
        owns = False
    try:
        fp.seek(chunk_meta["offset"])
        compressed = fp.read(chunk_meta["compressed_size"])
        if algorithm == "lz4":
            return lz4.frame.decompress(compressed)
        return zstd.ZstdDecompressor().decompress(compressed)
    finally:
        if owns:
            fp.close()
