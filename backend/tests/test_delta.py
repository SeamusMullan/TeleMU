"""Tests for delta compression of telemetry channels."""

import math

import pytest
import zstandard

from telemu.compression.delta import (
    DEFAULT_THRESHOLD,
    DEFAULT_THRESHOLDS,
    DeltaDecoder,
    DeltaEncoder,
    DeltaFrame,
    compress_frame,
    decompress_frame,
)


# ── DeltaFrame serialization ─────────────────────────────────────────────────


class TestDeltaFrame:
    def test_to_dict_and_back(self):
        frame = DeltaFrame(
            values={"speed": 5.0, "fuel": 80.0},
            absolute_channels=frozenset({"fuel"}),
        )
        d = frame.to_dict()
        restored = DeltaFrame.from_dict(d)
        assert restored.values == frame.values
        assert restored.absolute_channels == frame.absolute_channels

    def test_to_bytes_and_back(self):
        frame = DeltaFrame(
            values={"rpm": 100.0, "gear": 0.0},
            absolute_channels=frozenset({"rpm"}),
        )
        raw = frame.to_bytes()
        restored = DeltaFrame.from_bytes(raw)
        assert restored.values == frame.values
        assert restored.absolute_channels == frame.absolute_channels

    def test_empty_frame(self):
        frame = DeltaFrame()
        d = frame.to_dict()
        restored = DeltaFrame.from_dict(d)
        assert restored.values == {}
        assert restored.absolute_channels == frozenset()


# ── DeltaEncoder ──────────────────────────────────────────────────────────────


class TestDeltaEncoder:
    def test_first_frame_is_absolute(self):
        enc = DeltaEncoder()
        channels = {"speed": 200.0, "fuel": 80.0, "gear": 4.0}
        frame = enc.encode(channels)
        # First frame: all channels stored as absolute
        assert frame.absolute_channels == frozenset(channels.keys())
        assert frame.values == channels

    def test_unchanged_values_are_zero(self):
        enc = DeltaEncoder()
        channels = {"speed": 200.0, "fuel": 80.0}
        enc.encode(channels)  # first frame
        frame = enc.encode(channels)  # same values
        assert frame.absolute_channels == frozenset()
        assert frame.values == {"speed": 0.0, "fuel": 0.0}

    def test_delta_encoding(self):
        enc = DeltaEncoder()
        enc.encode({"speed": 200.0})
        frame = enc.encode({"speed": 210.0})
        assert frame.values["speed"] == pytest.approx(10.0)
        assert "speed" not in frame.absolute_channels

    def test_threshold_suppresses_small_delta(self):
        enc = DeltaEncoder(thresholds={"fuel": 0.01})
        enc.encode({"fuel": 80.0})
        # Small change below threshold
        frame = enc.encode({"fuel": 80.005})
        assert frame.values["fuel"] == 0.0

    def test_threshold_passes_large_delta(self):
        enc = DeltaEncoder(thresholds={"fuel": 0.01})
        enc.encode({"fuel": 80.0})
        frame = enc.encode({"fuel": 79.95})
        assert frame.values["fuel"] == pytest.approx(-0.05)

    def test_accumulated_threshold_catchup(self):
        """Small deltas accumulate until they exceed the threshold."""
        enc = DeltaEncoder(thresholds={"fuel": 0.1})
        enc.encode({"fuel": 80.0})
        # Small change below threshold
        frame = enc.encode({"fuel": 79.95})
        assert frame.values["fuel"] == 0.0  # suppressed (delta=0.05 < 0.1)
        # Larger accumulated change exceeds threshold
        frame = enc.encode({"fuel": 79.8})
        # Delta = 79.8 - 80.0 = -0.2, abs(0.2) > 0.1, so it should pass
        assert frame.values["fuel"] == pytest.approx(-0.2)

    def test_default_threshold_for_unknown_channel(self):
        enc = DeltaEncoder(default_threshold=0.5)
        enc.encode({"custom": 100.0})
        frame = enc.encode({"custom": 100.3})
        # 0.3 <= 0.5 threshold, suppressed
        assert frame.values["custom"] == 0.0

    def test_new_channel_in_later_frame(self):
        enc = DeltaEncoder()
        enc.encode({"speed": 200.0})
        frame = enc.encode({"speed": 205.0, "fuel": 80.0})
        assert "fuel" in frame.absolute_channels
        assert "speed" not in frame.absolute_channels
        assert frame.values["fuel"] == 80.0
        assert frame.values["speed"] == pytest.approx(5.0)

    def test_reset(self):
        enc = DeltaEncoder()
        enc.encode({"speed": 200.0})
        enc.reset()
        frame = enc.encode({"speed": 200.0})
        # After reset, first frame again
        assert frame.absolute_channels == frozenset({"speed"})

    def test_negative_delta(self):
        enc = DeltaEncoder()
        enc.encode({"speed": 200.0})
        frame = enc.encode({"speed": 180.0})
        assert frame.values["speed"] == pytest.approx(-20.0)


# ── DeltaDecoder ──────────────────────────────────────────────────────────────


class TestDeltaDecoder:
    def test_decode_absolute(self):
        dec = DeltaDecoder()
        frame = DeltaFrame(
            values={"speed": 200.0},
            absolute_channels=frozenset({"speed"}),
        )
        result = dec.decode(frame)
        assert result == {"speed": 200.0}

    def test_decode_delta(self):
        dec = DeltaDecoder()
        # Absolute frame
        dec.decode(DeltaFrame(
            values={"speed": 200.0},
            absolute_channels=frozenset({"speed"}),
        ))
        # Delta frame
        result = dec.decode(DeltaFrame(
            values={"speed": 10.0},
            absolute_channels=frozenset(),
        ))
        assert result["speed"] == pytest.approx(210.0)

    def test_decode_zero_delta(self):
        dec = DeltaDecoder()
        dec.decode(DeltaFrame(
            values={"fuel": 80.0},
            absolute_channels=frozenset({"fuel"}),
        ))
        result = dec.decode(DeltaFrame(
            values={"fuel": 0.0},
            absolute_channels=frozenset(),
        ))
        assert result["fuel"] == pytest.approx(80.0)

    def test_reset(self):
        dec = DeltaDecoder()
        dec.decode(DeltaFrame(
            values={"speed": 200.0},
            absolute_channels=frozenset({"speed"}),
        ))
        dec.reset()
        # After reset, delta without prior absolute uses 0.0 as base
        result = dec.decode(DeltaFrame(
            values={"speed": 50.0},
            absolute_channels=frozenset(),
        ))
        assert result["speed"] == pytest.approx(50.0)


# ── Round-trip (encoder → decoder) ───────────────────────────────────────────


class TestRoundTrip:
    def test_single_frame(self):
        enc = DeltaEncoder()
        dec = DeltaDecoder()
        channels = {"speed": 200.0, "fuel": 80.0, "gear": 4.0}
        decoded = dec.decode(enc.encode(channels))
        assert decoded == pytest.approx(channels)

    def test_multiple_frames(self):
        enc = DeltaEncoder()
        dec = DeltaDecoder()
        frames = [
            {"speed": 200.0, "fuel": 80.0, "gear": 4.0},
            {"speed": 210.0, "fuel": 79.99, "gear": 4.0},
            {"speed": 215.0, "fuel": 79.98, "gear": 5.0},
            {"speed": 190.0, "fuel": 79.97, "gear": 3.0},
        ]
        for channels in frames:
            decoded = dec.decode(enc.encode(channels))
            assert decoded == pytest.approx(channels)

    def test_round_trip_with_threshold(self):
        """With thresholds, decoded values may differ within threshold bounds."""
        enc = DeltaEncoder(thresholds={"fuel": 0.01})
        dec = DeltaDecoder()

        enc_frame = enc.encode({"fuel": 80.0})
        dec.decode(enc_frame)

        # Small change below threshold — suppressed
        enc_frame = enc.encode({"fuel": 79.995})
        decoded = dec.decode(enc_frame)
        # Decoder still has 80.0 (delta was suppressed)
        assert decoded["fuel"] == pytest.approx(80.0)

        # Larger change that exceeds threshold from the encoder's tracked value
        enc_frame = enc.encode({"fuel": 79.98})
        decoded = dec.decode(enc_frame)
        assert decoded["fuel"] == pytest.approx(79.98)

    def test_round_trip_simulated_telemetry(self):
        """Round-trip with simulated racing telemetry (like DemoReader).

        With default thresholds, slowly-changing channels (fuel) may have
        small deltas suppressed, so decoded values can differ up to the
        configured threshold.
        """
        enc = DeltaEncoder(thresholds={}, default_threshold=0.0)
        dec = DeltaDecoder()

        for i in range(100):
            t = i * 0.016
            channels = {
                "speed": 180 + 100 * math.sin(t * 0.3),
                "rpm": 4000 + 4000 * (0.5 + 0.5 * math.sin(t * 0.5)),
                "throttle": max(0, min(100, 50 + 50 * math.sin(t * 0.4))),
                "brake": max(0, min(100, 30 * max(0, -math.sin(t * 0.4)))),
                "gear": float(max(1, min(7, int(3.5 + 3 * math.sin(t * 0.2))))),
                "steering": 30 * math.sin(t * 0.8),
                "fuel": max(0, 80 - t * 0.05),
                "fuel_capacity": 110.0,
                "rpm_max": 8500.0,
            }
            decoded = dec.decode(enc.encode(channels))
            assert decoded == pytest.approx(channels)


# ── compress_frame / decompress_frame ─────────────────────────────────────────


class TestCompressDecompress:
    def test_round_trip(self):
        enc = DeltaEncoder()
        dec = DeltaDecoder()
        channels = {"speed": 200.0, "fuel": 80.0, "gear": 4.0}
        compressed = compress_frame(channels, enc)
        assert isinstance(compressed, bytes)
        decoded = decompress_frame(compressed, dec)
        assert decoded == pytest.approx(channels)

    def test_multiple_frames(self):
        enc = DeltaEncoder()
        dec = DeltaDecoder()
        frames = [
            {"speed": 200.0, "fuel": 80.0},
            {"speed": 210.0, "fuel": 79.99},
            {"speed": 215.0, "fuel": 79.98},
        ]
        for channels in frames:
            compressed = compress_frame(channels, enc)
            decoded = decompress_frame(compressed, dec)
            assert decoded == pytest.approx(channels)

    def test_delta_frames_compress_smaller(self):
        """Delta-encoded frames should compress smaller than raw zstd on
        slowly-changing data, demonstrating the improvement."""
        enc = DeltaEncoder()
        zstd = zstandard.ZstdCompressor(level=3)

        raw_sizes = []
        delta_sizes = []

        for i in range(50):
            t = i * 0.016
            channels = {
                "speed": 180 + 100 * math.sin(t * 0.3),
                "fuel": max(0, 80 - t * 0.05),
                "fuel_capacity": 110.0,
                "rpm_max": 8500.0,
                "gear": float(max(1, min(7, int(3.5 + 3 * math.sin(t * 0.2))))),
                "tyre_fl": 85 + 10 * math.sin(t * 0.1),
                "tyre_fr": 87 + 10 * math.sin(t * 0.1 + 0.5),
            }

            # Raw zstd (no delta encoding)
            import json
            raw_bytes = json.dumps(channels, separators=(",", ":")).encode()
            raw_compressed = zstd.compress(raw_bytes)
            raw_sizes.append(len(raw_compressed))

            # Delta + zstd
            delta_compressed = compress_frame(channels, enc)
            delta_sizes.append(len(delta_compressed))

        total_raw = sum(raw_sizes)
        total_delta = sum(delta_sizes)

        # Delta encoding should save space (skip first frame which is absolute)
        # The first frame is the same size, but subsequent frames should be smaller
        delta_after_first = sum(delta_sizes[1:])
        raw_after_first = sum(raw_sizes[1:])

        assert delta_after_first < raw_after_first, (
            f"Delta ({delta_after_first}B) should be smaller than raw "
            f"({raw_after_first}B) for slowly-changing data"
        )
