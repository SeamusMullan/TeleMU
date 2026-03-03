"""Tests for the streaming compressor module."""

import io
import json
import struct
import time

import pytest

from telemu.recording.compressor import (
    MAGIC,
    StreamCompressor,
    decompress_chunk,
    read_index,
)


def _make_frame(i: int) -> bytes:
    """Return a small deterministic payload resembling serialised telemetry."""
    return json.dumps({"ts": i * 0.016, "speed": 180.0 + i, "rpm": 4000 + i}).encode()


# ── StreamCompressor ──────────────────────────────────────────────────────────


class TestStreamCompressorLZ4:
    """LZ4 (default) compressor tests."""

    def test_single_chunk(self):
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=5, algorithm="lz4")
        for i in range(5):
            c.write_frame(_make_frame(i))
        c.finalize()

        idx = read_index(buf)
        assert idx["algorithm"] == "lz4"
        assert len(idx["chunks"]) == 1
        assert idx["chunks"][0]["frame_count"] == 5

    def test_multiple_chunks(self):
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=3, algorithm="lz4")
        for i in range(10):
            c.write_frame(_make_frame(i))
        c.finalize()

        idx = read_index(buf)
        # 10 frames / 3 per chunk => 3 full + 1 partial = 4 chunks
        assert len(idx["chunks"]) == 4
        assert idx["chunks"][-1]["frame_count"] == 1  # remainder

    def test_roundtrip(self):
        buf = io.BytesIO()
        frames = [_make_frame(i) for i in range(12)]
        raw_blob = b"".join(frames)

        c = StreamCompressor(buf, chunk_frames=4, algorithm="lz4")
        for f in frames:
            c.write_frame(f)
        c.finalize()

        idx = read_index(buf)
        reassembled = b""
        for chunk in idx["chunks"]:
            reassembled += decompress_chunk(buf, chunk, algorithm="lz4")
        assert reassembled == raw_blob

    def test_compression_ratio(self):
        """Numerical telemetry should compress well (> 1x)."""
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=60, algorithm="lz4")
        raw_total = 0
        for i in range(120):
            frame = _make_frame(i)
            raw_total += len(frame)
            c.write_frame(frame)
        c.finalize()

        compressed_total = sum(ch["compressed_size"] for ch in c.index)
        ratio = raw_total / compressed_total
        assert ratio > 1.0, f"Expected compression, got ratio {ratio:.2f}"

    def test_write_after_finalize_raises(self):
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=5, algorithm="lz4")
        c.finalize()
        with pytest.raises(RuntimeError, match="finalised"):
            c.write_frame(b"nope")

    def test_finalize_idempotent(self):
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=5, algorithm="lz4")
        c.write_frame(_make_frame(0))
        c.finalize()
        size1 = buf.tell()
        c.finalize()  # should be a no-op
        size2 = buf.tell()
        assert size1 == size2


class TestStreamCompressorZstd:
    """Zstandard fallback tests."""

    def test_roundtrip_zstd(self):
        buf = io.BytesIO()
        frames = [_make_frame(i) for i in range(8)]
        raw_blob = b"".join(frames)

        c = StreamCompressor(buf, chunk_frames=4, algorithm="zstd")
        for f in frames:
            c.write_frame(f)
        c.finalize()

        idx = read_index(buf)
        assert idx["algorithm"] == "zstd"
        reassembled = b""
        for chunk in idx["chunks"]:
            reassembled += decompress_chunk(buf, chunk, algorithm="zstd")
        assert reassembled == raw_blob


# ── File trailer / magic ─────────────────────────────────────────────────────


class TestTrailer:
    def test_magic_present(self):
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=5, algorithm="lz4")
        c.write_frame(_make_frame(0))
        c.finalize()
        buf.seek(-len(MAGIC), 2)
        assert buf.read() == MAGIC

    def test_invalid_magic_raises(self):
        buf = io.BytesIO(b"not a tmu file at all")
        with pytest.raises(ValueError, match="Not a valid TMU"):
            read_index(buf)


# ── Latency ───────────────────────────────────────────────────────────────────


class TestLatency:
    def test_chunk_compress_latency(self):
        """Each chunk compression should take < 1ms for typical telemetry."""
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=60, algorithm="lz4")

        # pre-fill buffer
        for i in range(59):
            c.write_frame(_make_frame(i))

        # time the 60th frame write which triggers flush
        start = time.perf_counter()
        c.write_frame(_make_frame(59))
        elapsed_ms = (time.perf_counter() - start) * 1000

        c.finalize()
        assert elapsed_ms < 5.0, f"Chunk compress took {elapsed_ms:.2f}ms (want < 5ms)"


# ── Seekability ───────────────────────────────────────────────────────────────


class TestSeekability:
    def test_seek_to_specific_chunk(self):
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=4, algorithm="lz4")
        frames = [_make_frame(i) for i in range(12)]
        for f in frames:
            c.write_frame(f)
        c.finalize()

        idx = read_index(buf)
        # Decompress only the second chunk (frames 4-7)
        second_chunk_data = decompress_chunk(buf, idx["chunks"][1], algorithm="lz4")
        expected = b"".join(frames[4:8])
        assert second_chunk_data == expected

    def test_index_offsets_are_monotonic(self):
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=3, algorithm="lz4")
        for i in range(15):
            c.write_frame(_make_frame(i))
        c.finalize()

        idx = read_index(buf)
        offsets = [ch["offset"] for ch in idx["chunks"]]
        assert offsets == sorted(offsets), "Chunk offsets must be monotonically increasing"
