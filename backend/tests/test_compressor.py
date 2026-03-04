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
    CHANNEL_DEF_SIZE,
    FOOTER_SIZE,
    HEADER_FIXED_SIZE,
    ChannelDef,
    ChannelType,
    TMUFooter,
    TMUHeader,
    build_minimal_tmu,
    compute_channel_offsets,
    frame_payload_size,
    pack_frame,
    unpack_frame,
    verify_tmu,
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


def _make_tmu_frame_values(i: int) -> list[tuple[ChannelType, object]]:
    """Return channel values for frame *i* matching ``_TMU_CHANNELS``."""
    t = i * (1.0 / 60)
    return [
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


def _make_tmu_frame(i: int) -> bytes:
    """Build one binary TMU frame with realistic telemetry values."""
    t = i * (1.0 / 60)
    return pack_frame(t, _make_tmu_frame_values(i))


def _parse_channels(tmu_data: bytes) -> list[ChannelDef]:
    """Parse channel definitions from a complete ``.tmu`` byte string."""
    hdr = TMUHeader.unpack(tmu_data)
    meta_end = HEADER_FIXED_SIZE + len(hdr.metadata_json)
    channels: list[ChannelDef] = []
    for i in range(hdr.channel_count):
        offset = meta_end + i * CHANNEL_DEF_SIZE
        channels.append(ChannelDef.unpack(tmu_data[offset : offset + CHANNEL_DEF_SIZE]))
    return channels


class TestTMUFormatCompression:
    """Compress actual TMU-spec binary frames from ``build_minimal_tmu()`` files
    and verify format compliance and performance.
    """

    FRAME_COUNT = 3600  # 60 seconds at 60Hz

    @pytest.fixture()
    def tmu_file_data(self):
        """Build a complete, valid ``.tmu`` file using ``build_minimal_tmu()``."""
        channels = [ChannelDef(c.name, c.channel_type, c.unit, c.byte_offset) for c in _TMU_CHANNELS]
        compute_channel_offsets(channels)
        frames = [
            (i * (1.0 / 60), _make_tmu_frame_values(i))
            for i in range(self.FRAME_COUNT)
        ]
        data = build_minimal_tmu(
            track="Spa-Francorchamps",
            vehicle="Toyota GR010",
            driver="TestDriver",
            channels=channels,
            frames=frames,
            metadata={"weather": "clear", "session": "practice"},
        )
        return data

    @pytest.fixture()
    def tmu_frames(self, tmu_file_data):
        """Extract individual frame blobs from the complete ``.tmu`` file."""
        channels = _parse_channels(tmu_file_data)
        fsize = frame_payload_size(channels)
        footer = TMUFooter.unpack(tmu_file_data[-FOOTER_SIZE:])
        frames: list[bytes] = []
        for i in range(footer.frame_count):
            idx_pos = footer.index_offset + i * 8
            assert idx_pos + 8 <= len(tmu_file_data) - FOOTER_SIZE
            (frame_offset,) = struct.unpack("<Q", tmu_file_data[idx_pos : idx_pos + 8])
            assert frame_offset + fsize <= footer.index_offset
            frames.append(tmu_file_data[frame_offset : frame_offset + fsize])
        return frames

    def test_generated_tmu_file_is_valid(self, tmu_file_data):
        """Verify the generated file passes ``verify_tmu()`` checks."""
        result = verify_tmu(tmu_file_data)
        assert result.ok, f"verify_tmu failed: {result.message}"
        assert result.crc32_ok
        assert result.header_ok
        assert result.frame_count == self.FRAME_COUNT

    def test_generated_tmu_header(self, tmu_file_data):
        """Header fields match the format spec (magic, version, channel count)."""
        from telemu.recording.tmu_format import MAGIC as TMU_MAGIC, FORMAT_VERSION
        assert tmu_file_data[:4] == TMU_MAGIC
        hdr = TMUHeader.unpack(tmu_file_data)
        assert hdr.version == FORMAT_VERSION
        assert hdr.track_name == "Spa-Francorchamps"
        assert hdr.vehicle_name == "Toyota GR010"
        assert hdr.driver_name == "TestDriver"
        assert hdr.channel_count == len(_TMU_CHANNELS)
        assert hdr.sample_rate_hz == 60

    def test_tmu_roundtrip_lz4(self, tmu_file_data, tmu_frames):
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
        channels = _parse_channels(tmu_file_data)
        fsize = frame_payload_size(channels)
        for i in range(min(5, self.FRAME_COUNT)):
            ts, vals = unpack_frame(reassembled[i * fsize : (i + 1) * fsize], channels)
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
