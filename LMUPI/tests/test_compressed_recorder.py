"""Tests for compressed_recorder — LZ4 and zstd chunk-compressed recording."""

from __future__ import annotations

import os
import struct
import time

import pytest

from lmupi.compressed_recorder import (
    MAGIC,
    CompressedReader,
    CompressedRecorder,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frame(idx: int, size: int = 256) -> bytes:
    """Return a deterministic frame of *size* bytes for testing."""
    return bytes([idx & 0xFF] * size)


def _make_telemetry_frame(idx: int) -> bytes:
    """Simulate a realistic numerical telemetry frame (floats)."""
    import struct as _s

    values = [
        200.0 + idx * 0.1,   # speed
        8000.0 + idx * 0.5,  # rpm
        0.75,                 # throttle
        0.0,                  # brake
        4.0,                  # gear
        0.02,                 # steering
        95.0,                 # tyre_fl
        96.0,                 # tyre_fr
        94.0,                 # tyre_rl
        93.0,                 # tyre_rr
        45.0,                 # fuel
        350.0,                # brake_temp
        0.0,                  # drs
        0.0,                  # pit
        0.0,                  # flag
        float(idx),           # timestamp
    ]
    return _s.pack(f"<{len(values)}f", *values)


# ---------------------------------------------------------------------------
# Basic round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Write frames, finalize, read back — data must match."""

    @pytest.mark.parametrize("compressor", ["lz4", "zstd"])
    def test_basic_roundtrip(self, compressor: str, tmp_path):
        path = tmp_path / "test.tlm"
        frames = [_make_frame(i) for i in range(100)]

        rec = CompressedRecorder(path, compressor=compressor, chunk_frames=32)
        rec.start()
        for f in frames:
            rec.write_frame(f)
        rec.finalize()

        with CompressedReader(path) as reader:
            assert reader.total_frames == 100
            assert reader.compressor == compressor
            recovered = list(reader.iter_frames())

        assert len(recovered) == len(frames)
        for orig, got in zip(frames, recovered):
            assert orig == got

    def test_single_frame_chunk(self, tmp_path):
        """Even with chunk_frames=1, round-trip must work."""
        path = tmp_path / "single.tlm"
        frames = [_make_frame(i, size=64) for i in range(10)]

        rec = CompressedRecorder(path, chunk_frames=1)
        rec.start()
        for f in frames:
            rec.write_frame(f)
        rec.finalize()

        with CompressedReader(path) as reader:
            assert reader.total_chunks == 10
            assert reader.total_frames == 10
            assert list(reader.iter_frames()) == frames

    def test_partial_last_chunk(self, tmp_path):
        """Frames that don't fill the last chunk must still be written."""
        path = tmp_path / "partial.tlm"
        frames = [_make_frame(i) for i in range(50)]

        rec = CompressedRecorder(path, chunk_frames=32)
        rec.start()
        for f in frames:
            rec.write_frame(f)
        rec.finalize()

        with CompressedReader(path) as reader:
            assert reader.total_frames == 50
            assert reader.total_chunks == 2
            assert list(reader.iter_frames()) == frames


# ---------------------------------------------------------------------------
# Random access via chunk index
# ---------------------------------------------------------------------------


class TestRandomAccess:
    def test_read_chunk_by_index(self, tmp_path):
        path = tmp_path / "seek.tlm"
        chunk_size = 16
        n_frames = 80
        frames = [_make_frame(i, size=128) for i in range(n_frames)]

        rec = CompressedRecorder(path, chunk_frames=chunk_size)
        rec.start()
        for f in frames:
            rec.write_frame(f)
        rec.finalize()

        with CompressedReader(path) as reader:
            assert reader.total_chunks == 5  # 80 / 16
            chunk3 = reader.read_chunk(3)
            expected = frames[48:64]
            assert chunk3 == expected

    def test_chunk_index_out_of_range(self, tmp_path):
        path = tmp_path / "oob.tlm"
        rec = CompressedRecorder(path, chunk_frames=8)
        rec.start()
        for i in range(8):
            rec.write_frame(_make_frame(i))
        rec.finalize()

        with CompressedReader(path) as reader:
            with pytest.raises(IndexError):
                reader.read_chunk(5)


# ---------------------------------------------------------------------------
# Compression effectiveness
# ---------------------------------------------------------------------------


class TestCompression:
    def test_file_smaller_than_raw(self, tmp_path):
        """Compressed file should be significantly smaller than raw data."""
        path = tmp_path / "ratio.tlm"
        frames = [_make_telemetry_frame(i) for i in range(1000)]
        raw_size = sum(len(f) for f in frames)

        rec = CompressedRecorder(path, chunk_frames=64)
        rec.start()
        for f in frames:
            rec.write_frame(f)
        rec.finalize()

        compressed_size = path.stat().st_size
        ratio = raw_size / compressed_size
        assert ratio > 2.0, f"Compression ratio {ratio:.1f}x is too low"

    @pytest.mark.parametrize("compressor", ["lz4", "zstd"])
    def test_both_compressors_shrink(self, compressor, tmp_path):
        path = tmp_path / f"shrink_{compressor}.tlm"
        frames = [_make_telemetry_frame(i) for i in range(500)]
        raw_size = sum(len(f) for f in frames)

        rec = CompressedRecorder(path, compressor=compressor, chunk_frames=64)
        rec.start()
        for f in frames:
            rec.write_frame(f)
        rec.finalize()

        assert path.stat().st_size < raw_size


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------


class TestLatency:
    def test_write_latency_under_1ms(self, tmp_path):
        """Per-frame write_frame() call should be well under 1ms."""
        path = tmp_path / "latency.tlm"
        frame = _make_telemetry_frame(0)

        rec = CompressedRecorder(path, chunk_frames=64)
        rec.start()

        n = 1000
        t0 = time.perf_counter()
        for i in range(n):
            rec.write_frame(frame)
        t1 = time.perf_counter()
        rec.finalize()

        avg_us = (t1 - t0) / n * 1e6
        assert avg_us < 1000, f"Average write latency {avg_us:.0f} µs exceeds 1 ms"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_recording(self, tmp_path):
        """Finalize with zero frames should produce a valid (empty) file."""
        path = tmp_path / "empty.tlm"
        rec = CompressedRecorder(path, chunk_frames=32)
        rec.start()
        rec.finalize()

        with CompressedReader(path) as reader:
            assert reader.total_frames == 0
            assert reader.total_chunks == 0
            assert list(reader.iter_frames()) == []

    def test_finalize_without_start_is_noop(self, tmp_path):
        """Calling finalize() before start() should not raise."""
        rec = CompressedRecorder(tmp_path / "noop.tlm")
        rec.finalize()

    def test_write_before_start_raises(self, tmp_path):
        rec = CompressedRecorder(tmp_path / "nostart.tlm")
        with pytest.raises(RuntimeError):
            rec.write_frame(b"data")

    def test_double_start_raises(self, tmp_path):
        path = tmp_path / "double.tlm"
        rec = CompressedRecorder(path)
        rec.start()
        with pytest.raises(RuntimeError):
            rec.start()
        rec.finalize()

    def test_invalid_compressor_raises(self, tmp_path):
        with pytest.raises(ValueError):
            CompressedRecorder(tmp_path / "bad.tlm", compressor="deflate")

    def test_variable_frame_sizes(self, tmp_path):
        """Frames of different sizes must round-trip correctly."""
        path = tmp_path / "varsz.tlm"
        frames = [os.urandom(i * 10 + 1) for i in range(50)]

        rec = CompressedRecorder(path, chunk_frames=8)
        rec.start()
        for f in frames:
            rec.write_frame(f)
        rec.finalize()

        with CompressedReader(path) as reader:
            assert list(reader.iter_frames()) == frames


# ---------------------------------------------------------------------------
# File format validation
# ---------------------------------------------------------------------------


class TestFileFormat:
    def test_magic_and_version(self, tmp_path):
        path = tmp_path / "fmt.tlm"
        rec = CompressedRecorder(path)
        rec.start()
        rec.write_frame(b"hello")
        rec.finalize()

        with open(path, "rb") as f:
            magic = f.read(4)
            assert magic == MAGIC
            version = struct.unpack("<I", f.read(4))[0]
            assert version == 1

    def test_bad_magic_rejected(self, tmp_path):
        path = tmp_path / "bad_magic.tlm"
        with open(path, "wb") as f:
            f.write(b"BAAD" + b"\x00" * 28)

        with pytest.raises(ValueError, match="Bad magic"):
            with CompressedReader(path) as reader:
                pass
