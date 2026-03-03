"""LZ4 streaming compression for telemetry recordings.

Provides a streaming compressor that accumulates raw frames into chunks
and compresses each chunk with LZ4 frame compression.  A chunk index
is maintained so the file remains seekable after finalization.
"""

from __future__ import annotations

import lz4.frame

from lmupi.tmu_format import ChunkIndex


class StreamingCompressor:
    """Accumulates raw frame data and compresses in chunks.

    Args:
        frames_per_chunk: Number of frames to accumulate before compressing
            a chunk.  Larger values improve compression ratio; smaller values
            reduce latency and memory usage.
    """

    def __init__(self, frames_per_chunk: int = 64) -> None:
        self._frames_per_chunk = frames_per_chunk
        self._buffer = bytearray()
        self._frame_count = 0          # frames in current buffer
        self._total_frames = 0         # total frames across all chunks
        self._chunk_indices: list[ChunkIndex] = []

    @property
    def chunk_indices(self) -> list[ChunkIndex]:
        """Return the list of chunk index entries written so far."""
        return list(self._chunk_indices)

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def pending_frames(self) -> int:
        """Number of frames buffered but not yet compressed."""
        return self._frame_count

    def add_frame(self, frame_data: bytes) -> bytes | None:
        """Add a raw frame to the buffer.

        Returns:
            Compressed chunk bytes if the buffer is full, otherwise ``None``.
        """
        self._buffer.extend(frame_data)
        self._frame_count += 1
        self._total_frames += 1

        if self._frame_count >= self._frames_per_chunk:
            return self._flush_buffer()
        return None

    def flush(self) -> bytes | None:
        """Flush any remaining buffered frames as a compressed chunk.

        Returns:
            Compressed chunk bytes if there were pending frames, otherwise
            ``None``.
        """
        if self._frame_count > 0:
            return self._flush_buffer()
        return None

    def _flush_buffer(self) -> bytes:
        """Compress the current buffer and return compressed bytes."""
        compressed = lz4.frame.compress(
            bytes(self._buffer),
            compression_level=0,  # fast mode
            block_size=lz4.frame.BLOCKSIZE_MAX256KB,
        )

        first_frame_idx = self._total_frames - self._frame_count
        entry = ChunkIndex(
            file_offset=0,  # placeholder — set by caller
            compressed_size=len(compressed),
            frame_count=self._frame_count,
            first_frame_idx=first_frame_idx,
        )
        self._chunk_indices.append(entry)

        self._buffer.clear()
        self._frame_count = 0

        return compressed


def decompress_chunk(data: bytes) -> bytes:
    """Decompress a single LZ4-compressed chunk."""
    return lz4.frame.decompress(data)
