"""Tests for the .tmu format, binary serializer, LZ4 compression,
and TelemetryRecorder (excluding Qt/shared-memory integration)."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from lmupi.tmu_format import (
    CHUNK_INDEX_SIZE,
    FOOTER_SIZE,
    HEADER_SIZE,
    TMU_MAGIC,
    ChannelDef,
    ChannelType,
    ChunkIndex,
    SessionMetadata,
    decode_channel_table,
    decode_chunk_index,
    decode_footer,
    decode_header,
    encode_channel_table,
    encode_chunk_index,
    encode_footer,
    encode_header,
)
from lmupi.tmu_compression import StreamingCompressor, decompress_chunk
from lmupi.tmu_serializer import TelemetrySerializer, default_channels


# ── Helpers ───────────────────────────────────────────────

def _make_vect3(x=0.0, y=0.0, z=0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _make_wheel(temp_center=300.0, pressure=200.0, brake_temp=400.0):
    return SimpleNamespace(
        mTemperature=[0.0, temp_center, 0.0],
        mPressure=pressure,
        mBrakeTemp=brake_temp,
    )


def _make_vt(**overrides):
    """Create a mock LMUVehicleTelemetry namespace."""
    defaults = dict(
        mEngineRPM=5000.0,
        mUnfilteredThrottle=0.75,
        mUnfilteredBrake=0.1,
        mUnfilteredSteering=0.05,
        mPhysicalSteeringWheelRange=900.0,
        mGear=3,
        mUnfilteredClutch=0.0,
        mEngineWaterTemp=90.0,
        mEngineOilTemp=100.0,
        mEngineTorque=350.0,
        mEngineMaxRPM=8000.0,
        mFuel=40.0,
        mFuelCapacity=100.0,
        mLocalVel=_make_vect3(10.0, 0.0, 20.0),
        mLocalAccel=_make_vect3(1.0, 0.0, 2.0),
        mPos=_make_vect3(100.0, 5.0, 200.0),
        mLocalRot=_make_vect3(),
        mLocalRotAccel=_make_vect3(),
        mFrontRideHeight=0.05,
        mRearRideHeight=0.06,
        mDrag=1.2,
        mFrontDownforce=500.0,
        mRearDownforce=600.0,
        mCurrentSector=1,
        mElapsedTime=120.5,
        mDeltaTime=0.016,
        mWheels=[
            _make_wheel(350.0, 180.0, 400.0),
            _make_wheel(355.0, 182.0, 410.0),
            _make_wheel(340.0, 175.0, 380.0),
            _make_wheel(345.0, 177.0, 390.0),
        ],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_vs(**overrides):
    """Create a mock LMUVehicleScoring namespace."""
    defaults = dict(
        mTotalLaps=5,
        mLapDist=1500.0,
        mInPits=False,
        mLastLapTime=85.5,
        mBestLapTime=84.2,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── TMU Format Tests ─────────────────────────────────────

class TestTmuFormat(unittest.TestCase):
    def test_header_round_trip(self):
        header = encode_header(
            num_channels=10, sample_rate=60,
            metadata_offset=HEADER_SIZE, metadata_size=50,
            channel_table_offset=HEADER_SIZE + 50,
            channel_table_size=200,
            data_start_offset=HEADER_SIZE + 250,
        )
        self.assertEqual(len(header), HEADER_SIZE)
        decoded = decode_header(header)
        self.assertEqual(decoded["num_channels"], 10)
        self.assertEqual(decoded["sample_rate"], 60)
        self.assertEqual(decoded["metadata_offset"], HEADER_SIZE)

    def test_header_invalid_magic(self):
        bad = b"BAD\x00" + b"\x00" * (HEADER_SIZE - 4)
        with self.assertRaises(ValueError):
            decode_header(bad)

    def test_footer_round_trip(self):
        footer = encode_footer(total_frames=500, index_table_offset=10000, index_entry_count=8)
        self.assertEqual(len(footer), FOOTER_SIZE)
        decoded = decode_footer(footer)
        self.assertEqual(decoded["total_frames"], 500)
        self.assertEqual(decoded["index_table_offset"], 10000)
        self.assertEqual(decoded["index_entry_count"], 8)

    def test_channel_table_round_trip(self):
        channels = [
            ChannelDef("Speed", ChannelType.FLOAT64, "km/h", byte_offset=8),
            ChannelDef("Gear", ChannelType.INT32, "", byte_offset=16),
            ChannelDef("InPits", ChannelType.BOOL, "", byte_offset=20),
        ]
        encoded = encode_channel_table(channels)
        decoded = decode_channel_table(encoded, 3)
        self.assertEqual(len(decoded), 3)
        self.assertEqual(decoded[0].name, "Speed")
        self.assertEqual(decoded[0].type_code, ChannelType.FLOAT64)
        self.assertEqual(decoded[0].unit, "km/h")
        self.assertEqual(decoded[1].name, "Gear")
        self.assertEqual(decoded[2].name, "InPits")

    def test_chunk_index_round_trip(self):
        entry = ChunkIndex(file_offset=1024, compressed_size=256,
                           frame_count=64, first_frame_idx=128)
        encoded = encode_chunk_index(entry)
        self.assertEqual(len(encoded), CHUNK_INDEX_SIZE)
        decoded = decode_chunk_index(encoded)
        self.assertEqual(decoded.file_offset, 1024)
        self.assertEqual(decoded.compressed_size, 256)
        self.assertEqual(decoded.frame_count, 64)
        self.assertEqual(decoded.first_frame_idx, 128)

    def test_session_metadata_round_trip(self):
        meta = SessionMetadata(
            track="Spa-Francorchamps",
            car="Porsche 911 GT3 R",
            driver="Test Driver",
            date="2025-01-01T00:00:00Z",
            sample_rate=60,
            extra={"weather": "dry"},
        )
        json_bytes = meta.to_json_bytes()
        restored = SessionMetadata.from_json_bytes(json_bytes)
        self.assertEqual(restored.track, "Spa-Francorchamps")
        self.assertEqual(restored.car, "Porsche 911 GT3 R")
        self.assertEqual(restored.driver, "Test Driver")
        self.assertEqual(restored.sample_rate, 60)
        self.assertEqual(restored.extra.get("weather"), "dry")


# ── Compression Tests ─────────────────────────────────────

class TestStreamingCompressor(unittest.TestCase):
    def test_chunk_produced_at_threshold(self):
        comp = StreamingCompressor(frames_per_chunk=4)
        frame = b"\x42" * 100
        results = []
        for i in range(4):
            chunk = comp.add_frame(frame)
            results.append(chunk)
        # Only the 4th add_frame should produce a chunk
        self.assertIsNone(results[0])
        self.assertIsNone(results[1])
        self.assertIsNone(results[2])
        self.assertIsNotNone(results[3])
        self.assertEqual(comp.total_frames, 4)

    def test_decompress_round_trip(self):
        comp = StreamingCompressor(frames_per_chunk=2)
        frame = b"\xAB" * 50
        comp.add_frame(frame)
        chunk = comp.add_frame(frame)
        self.assertIsNotNone(chunk)
        raw = decompress_chunk(chunk)
        self.assertEqual(raw, frame * 2)

    def test_flush_remaining(self):
        comp = StreamingCompressor(frames_per_chunk=10)
        frame = b"\x01" * 32
        for _ in range(3):
            comp.add_frame(frame)
        self.assertEqual(comp.pending_frames, 3)
        chunk = comp.flush()
        self.assertIsNotNone(chunk)
        self.assertEqual(comp.pending_frames, 0)
        raw = decompress_chunk(chunk)
        self.assertEqual(raw, frame * 3)

    def test_flush_empty(self):
        comp = StreamingCompressor(frames_per_chunk=10)
        self.assertIsNone(comp.flush())

    def test_chunk_indices_maintained(self):
        comp = StreamingCompressor(frames_per_chunk=3)
        frame = b"\xFF" * 20
        for _ in range(9):
            comp.add_frame(frame)
        indices = comp.chunk_indices
        self.assertEqual(len(indices), 3)
        self.assertEqual(indices[0].first_frame_idx, 0)
        self.assertEqual(indices[0].frame_count, 3)
        self.assertEqual(indices[1].first_frame_idx, 3)
        self.assertEqual(indices[2].first_frame_idx, 6)
        self.assertEqual(comp.total_frames, 9)


# ── Serializer Tests ──────────────────────────────────────

class TestTelemetrySerializer(unittest.TestCase):
    def test_default_channels(self):
        channels = default_channels()
        self.assertGreater(len(channels), 10)
        names = [ch.name for ch in channels]
        self.assertIn("Speed", names)
        self.assertIn("RPM", names)
        self.assertIn("Gear", names)
        self.assertIn("Fuel", names)

    def test_frame_size(self):
        serializer = TelemetrySerializer()
        # frame = timestamp (8) + sum of all channel sizes
        expected = 8  # timestamp
        for ch in serializer.channels:
            from lmupi.tmu_format import CHANNEL_TYPE_SIZE
            expected += CHANNEL_TYPE_SIZE[ch.type_code]
        self.assertEqual(serializer.frame_size, expected)

    def test_serialize_frame(self):
        serializer = TelemetrySerializer()
        vt = _make_vt()
        vs = _make_vs()
        frame = serializer.serialize_frame(1.0, vt, vs)
        self.assertEqual(len(frame), serializer.frame_size)

        # Unpack and check timestamp
        timestamp = struct.unpack_from("<d", frame, 0)[0]
        self.assertAlmostEqual(timestamp, 1.0)

    def test_custom_channels(self):
        channels = [
            ChannelDef("RPM", ChannelType.FLOAT64, "rpm"),
            ChannelDef("Gear", ChannelType.INT32, ""),
        ]
        serializer = TelemetrySerializer(channels)
        self.assertEqual(len(serializer.channels), 2)
        # frame = timestamp(8) + double(8) + int32(4) = 20
        self.assertEqual(serializer.frame_size, 20)

        vt = _make_vt()
        vs = _make_vs()
        frame = serializer.serialize_frame(2.5, vt, vs)
        self.assertEqual(len(frame), 20)

        # Unpack: timestamp, rpm, gear
        ts, rpm, gear = struct.unpack("<ddi", frame)
        self.assertAlmostEqual(ts, 2.5)
        self.assertAlmostEqual(rpm, 5000.0)
        self.assertEqual(gear, 3)

    def test_speed_computation(self):
        """Speed should be sqrt(vx² + vy² + vz²) * 3.6."""
        import math
        channels = [ChannelDef("Speed", ChannelType.FLOAT64, "km/h")]
        serializer = TelemetrySerializer(channels)
        vt = _make_vt(mLocalVel=_make_vect3(10.0, 0.0, 0.0))
        vs = _make_vs()
        frame = serializer.serialize_frame(0.0, vt, vs)
        ts, speed = struct.unpack("<dd", frame)
        expected = math.sqrt(10.0**2) * 3.6
        self.assertAlmostEqual(speed, expected, places=5)

    def test_kelvin_to_celsius_conversion(self):
        """Tyre temps should be converted from Kelvin to Celsius."""
        channels = [ChannelDef("TyreTempFL", ChannelType.FLOAT64, "°C")]
        serializer = TelemetrySerializer(channels)
        vt = _make_vt()
        vs = _make_vs()
        frame = serializer.serialize_frame(0.0, vt, vs)
        ts, temp = struct.unpack("<dd", frame)
        # FL temp center is 350K → 350 - 273.15 = 76.85°C
        self.assertAlmostEqual(temp, 350.0 - 273.15, places=5)


# ── RingBuffer Tests (import without Qt) ──────────────────

class TestRingBufferLogic(unittest.TestCase):
    """Test ring buffer basic logic.  Since we can't import QMutex
    without PySide6 in CI, we test the deque-based logic directly."""

    def test_deque_ring_behavior(self):
        import collections
        buf = collections.deque(maxlen=4)
        for i in range(6):
            was_full = len(buf) == buf.maxlen
            buf.append(i)
        # maxlen=4 so oldest items dropped
        self.assertEqual(list(buf), [2, 3, 4, 5])


# ── Integration: Serializer → Compressor ──────────────────

class TestSerializerCompressorIntegration(unittest.TestCase):
    def test_end_to_end_frame_pipeline(self):
        """Serialize frames, compress them, then decompress and verify."""
        serializer = TelemetrySerializer()
        compressor = StreamingCompressor(frames_per_chunk=4)

        vt = _make_vt()
        vs = _make_vs()

        chunks = []
        for i in range(8):
            frame = serializer.serialize_frame(float(i), vt, vs)
            chunk = compressor.add_frame(frame)
            if chunk is not None:
                chunks.append(chunk)

        self.assertEqual(len(chunks), 2)  # 8 frames / 4 per chunk

        # Decompress first chunk and verify frame size
        raw = decompress_chunk(chunks[0])
        self.assertEqual(len(raw), serializer.frame_size * 4)

        # Verify first timestamp
        ts = struct.unpack_from("<d", raw, 0)[0]
        self.assertAlmostEqual(ts, 0.0)

    def test_file_write_simulation(self):
        """Simulate writing a complete .tmu file (header, data, index, footer)."""
        serializer = TelemetrySerializer()
        compressor = StreamingCompressor(frames_per_chunk=4)
        channels = serializer.channels

        meta = SessionMetadata(track="Test", car="TestCar", sample_rate=60)
        meta_bytes = meta.to_json_bytes()
        ch_table_bytes = encode_channel_table(channels)

        metadata_offset = HEADER_SIZE
        metadata_size = len(meta_bytes)
        channel_table_offset = metadata_offset + metadata_size
        channel_table_size = len(ch_table_bytes)
        data_start_offset = channel_table_offset + channel_table_size

        header = encode_header(
            num_channels=len(channels),
            sample_rate=60,
            metadata_offset=metadata_offset,
            metadata_size=metadata_size,
            channel_table_offset=channel_table_offset,
            channel_table_size=channel_table_size,
            data_start_offset=data_start_offset,
        )

        with tempfile.NamedTemporaryFile(suffix=".tmu", delete=False) as f:
            path = f.name
            f.write(header)
            f.write(meta_bytes)
            f.write(ch_table_bytes)

            bytes_written = data_start_offset
            vt = _make_vt()
            vs = _make_vs()

            for i in range(10):
                frame = serializer.serialize_frame(float(i), vt, vs)
                chunk = compressor.add_frame(frame)
                if chunk is not None:
                    idx_entry = compressor.chunk_indices[-1]
                    idx_entry.file_offset = bytes_written
                    f.write(chunk)
                    bytes_written += len(chunk)

            last = compressor.flush()
            if last is not None:
                idx_entry = compressor.chunk_indices[-1]
                idx_entry.file_offset = bytes_written
                f.write(last)
                bytes_written += len(last)

            index_offset = bytes_written
            for entry in compressor.chunk_indices:
                f.write(encode_chunk_index(entry))

            footer = encode_footer(
                total_frames=compressor.total_frames,
                index_table_offset=index_offset,
                index_entry_count=len(compressor.chunk_indices),
            )
            f.write(footer)

        # Read back and verify
        with open(path, "rb") as f:
            raw_header = f.read(HEADER_SIZE)
            hdr = decode_header(raw_header)
            self.assertEqual(hdr["num_channels"], len(channels))
            self.assertEqual(hdr["sample_rate"], 60)

            # Read metadata
            f.seek(hdr["metadata_offset"])
            raw_meta = f.read(hdr["metadata_size"])
            restored_meta = SessionMetadata.from_json_bytes(raw_meta)
            self.assertEqual(restored_meta.track, "Test")

            # Read footer
            f.seek(0, 2)
            file_size = f.tell()
            f.seek(file_size - FOOTER_SIZE)
            raw_footer = f.read(FOOTER_SIZE)
            ftr = decode_footer(raw_footer)
            self.assertEqual(ftr["total_frames"], 10)
            self.assertGreater(ftr["index_entry_count"], 0)

        Path(path).unlink()


if __name__ == "__main__":
    unittest.main()
