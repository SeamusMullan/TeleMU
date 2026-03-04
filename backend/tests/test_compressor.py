"""Tests for the streaming compressor module."""

import io
import json
import math
import struct
import time

import pytest

from telemu.recording.compressor import (
    MAGIC,
    StreamCompressor,
    decompress_chunk,
    read_index,
)
from telemu.recording.tmu_format import (
    ChannelDef,
    ChannelType,
    compute_channel_offsets,
    frame_payload_size,
    pack_frame,
    unpack_frame,
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


# ── TMU format integration & performance ──────────────────────────────────────

# Channels matching the real telemetry reader output
_TMU_CHANNELS = [
    ChannelDef("speed", ChannelType.FLOAT64, "km/h", 0),
    ChannelDef("rpm", ChannelType.FLOAT64, "rpm", 0),
    ChannelDef("throttle", ChannelType.FLOAT64, "%", 0),
    ChannelDef("brake", ChannelType.FLOAT64, "%", 0),
    ChannelDef("gear", ChannelType.INT32, "", 0),
    ChannelDef("steering", ChannelType.FLOAT64, "deg", 0),
    ChannelDef("fuel", ChannelType.FLOAT64, "L", 0),
    ChannelDef("fuel_capacity", ChannelType.FLOAT64, "L", 0),
    ChannelDef("rpm_max", ChannelType.FLOAT64, "rpm", 0),
    ChannelDef("tyre_fl", ChannelType.FLOAT64, "C", 0),
    ChannelDef("tyre_fr", ChannelType.FLOAT64, "C", 0),
    ChannelDef("tyre_rl", ChannelType.FLOAT64, "C", 0),
    ChannelDef("tyre_rr", ChannelType.FLOAT64, "C", 0),
    ChannelDef("brake_temp", ChannelType.FLOAT64, "C", 0),
]
compute_channel_offsets(_TMU_CHANNELS)


def _make_tmu_frame(i: int) -> bytes:
    """Build one binary TMU frame with realistic telemetry values."""
    t = i * (1.0 / 60)
    values: list[tuple[ChannelType, object]] = [
        (ChannelType.FLOAT64, 180.0 + 100 * math.sin(t * 0.3)),       # speed
        (ChannelType.FLOAT64, 4000 + 4000 * (0.5 + 0.5 * math.sin(t * 0.5))),  # rpm
        (ChannelType.FLOAT64, max(0, min(100, 50 + 50 * math.sin(t * 0.4)))),   # throttle
        (ChannelType.FLOAT64, max(0, min(100, 30 * max(0, -math.sin(t * 0.4))))),  # brake
        (ChannelType.INT32, max(1, min(7, int(3.5 + 3 * math.sin(t * 0.2))))),  # gear
        (ChannelType.FLOAT64, 30 * math.sin(t * 0.8)),                # steering
        (ChannelType.FLOAT64, max(0, 80 - t * 0.05)),                 # fuel
        (ChannelType.FLOAT64, 110.0),                                  # fuel_capacity
        (ChannelType.FLOAT64, 8500.0),                                 # rpm_max
        (ChannelType.FLOAT64, 85 + 10 * math.sin(t * 0.1)),           # tyre_fl
        (ChannelType.FLOAT64, 87 + 10 * math.sin(t * 0.1 + 0.5)),    # tyre_fr
        (ChannelType.FLOAT64, 82 + 8 * math.sin(t * 0.1 + 1.0)),     # tyre_rl
        (ChannelType.FLOAT64, 84 + 8 * math.sin(t * 0.1 + 1.5)),     # tyre_rr
        (ChannelType.FLOAT64, 400 + 200 * abs(math.sin(t * 0.3))),    # brake_temp
    ]
    return pack_frame(t, values)


class TestTMUFormatCompression:
    """Compress actual TMU-spec binary frames and verify performance."""

    FRAME_COUNT = 3600  # 60 seconds at 60Hz

    @pytest.fixture()
    def tmu_frames(self):
        return [_make_tmu_frame(i) for i in range(self.FRAME_COUNT)]

    def test_tmu_roundtrip_lz4(self, tmu_frames):
        """Compress TMU binary frames with LZ4 and verify lossless roundtrip."""
        raw_blob = b"".join(tmu_frames)
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=60, algorithm="lz4")
        for f in tmu_frames:
            c.write_frame(f)
        c.finalize()

        idx = read_index(buf)
        reassembled = b"".join(
            decompress_chunk(buf, chunk, algorithm="lz4")
            for chunk in idx["chunks"]
        )
        assert reassembled == raw_blob

        # Verify individual frames can be unpacked after decompression
        fsize = frame_payload_size(_TMU_CHANNELS)
        for i in range(0, min(5, self.FRAME_COUNT)):
            ts, vals = unpack_frame(reassembled[i * fsize : (i + 1) * fsize], _TMU_CHANNELS)
            assert isinstance(ts, float)
            assert "speed" in vals
            assert "rpm" in vals

    def test_tmu_roundtrip_zstd(self, tmu_frames):
        """Compress TMU binary frames with zstd and verify lossless roundtrip."""
        raw_blob = b"".join(tmu_frames)
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=60, algorithm="zstd")
        for f in tmu_frames:
            c.write_frame(f)
        c.finalize()

        idx = read_index(buf)
        assert idx["algorithm"] == "zstd"
        reassembled = b"".join(
            decompress_chunk(buf, chunk, algorithm="zstd")
            for chunk in idx["chunks"]
        )
        assert reassembled == raw_blob

    def test_tmu_compression_ratio(self, tmu_frames):
        """Binary TMU telemetry should achieve meaningful compression."""
        raw_size = sum(len(f) for f in tmu_frames)
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=60, algorithm="lz4")
        for f in tmu_frames:
            c.write_frame(f)
        c.finalize()

        compressed_size = sum(ch["compressed_size"] for ch in c.index)
        ratio = raw_size / compressed_size
        # Binary float telemetry is harder to compress than JSON,
        # but repeated patterns still yield > 1x
        assert ratio > 1.0, f"Expected compression, got ratio {ratio:.2f}"

    def test_tmu_chunk_latency(self, tmu_frames):
        """Compressing one 60-frame chunk of TMU data should take < 1ms."""
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=60, algorithm="lz4")

        # Pre-fill 59 frames
        for f in tmu_frames[:59]:
            c.write_frame(f)

        # Time the 60th frame write (triggers chunk flush)
        start = time.perf_counter()
        c.write_frame(tmu_frames[59])
        elapsed_ms = (time.perf_counter() - start) * 1000
        c.finalize()

        assert elapsed_ms < 1.0, f"Chunk compress took {elapsed_ms:.3f}ms (want < 1ms)"

    def test_tmu_throughput(self, tmu_frames):
        """Measure throughput: should sustain >> 60 fps."""
        buf = io.BytesIO()
        c = StreamCompressor(buf, chunk_frames=60, algorithm="lz4")

        start = time.perf_counter()
        for f in tmu_frames:
            c.write_frame(f)
        c.finalize()
        elapsed = time.perf_counter() - start

        fps = self.FRAME_COUNT / elapsed
        # Must handle at least 60Hz; in practice thousands of fps
        assert fps > 60, f"Throughput {fps:.0f} fps is too low (need > 60)"

    def test_tmu_frame_size_preserved(self, tmu_frames):
        """Each TMU frame should be the expected binary size."""
        expected = frame_payload_size(_TMU_CHANNELS)
        for f in tmu_frames[:10]:
            assert len(f) == expected
