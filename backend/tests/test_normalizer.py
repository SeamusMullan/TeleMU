"""Tests for the telemetry sample-rate normalizer."""

from __future__ import annotations

import math

import numpy as np
import pytest

from telemu.recording.normalizer import (
    NormalizationResult,
    _DISCRETE_CHANNELS,
    estimate_sample_rate,
    normalize_channel_data,
    normalize_frames,
)
from telemu.recording.tmu_ndjson import TmuFrame, TmuHeader


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_frames(
    rate_hz: float,
    duration_s: float,
    channels: dict[str, callable] | None = None,
) -> list[TmuFrame]:
    """Generate synthetic frames at a given rate.

    *channels* maps channel name → f(t) producing a value for time *t*.
    """
    if channels is None:
        channels = {
            "speed": lambda t: 100.0 + 50.0 * math.sin(t),
            "rpm": lambda t: 5000.0 + 2000.0 * math.sin(t * 2),
        }
    dt = 1.0 / rate_hz
    n = int(duration_s * rate_hz) + 1
    frames: list[TmuFrame] = []
    for i in range(n):
        t = i * dt
        vals = {name: fn(t) for name, fn in channels.items()}
        frames.append(TmuFrame(ts=t, channels=vals))
    return frames


# ── estimate_sample_rate ────────────────────────────────────────────────────


class TestEstimateSampleRate:
    def test_60hz(self):
        ts = np.arange(0, 1.0, 1.0 / 60, dtype=np.float64)
        rate = estimate_sample_rate(ts)
        assert abs(rate - 60.0) < 0.5

    def test_30hz(self):
        ts = np.arange(0, 1.0, 1.0 / 30, dtype=np.float64)
        rate = estimate_sample_rate(ts)
        assert abs(rate - 30.0) < 0.5

    def test_single_sample_returns_zero(self):
        assert estimate_sample_rate(np.array([1.0])) == 0.0

    def test_empty_returns_zero(self):
        assert estimate_sample_rate(np.array([])) == 0.0

    def test_robust_to_jitter(self):
        """Median-based rate should tolerate occasional dropped frames."""
        ts = np.arange(0, 1.0, 1.0 / 60, dtype=np.float64)
        # Remove ~10% of frames randomly to simulate drops
        rng = np.random.default_rng(42)
        keep = rng.random(len(ts)) > 0.1
        keep[0] = True  # keep at least first and last
        keep[-1] = True
        ts_jittered = ts[keep]
        rate = estimate_sample_rate(ts_jittered)
        # Should still be close to 60 Hz
        assert abs(rate - 60.0) < 5.0


# ── normalize_channel_data ──────────────────────────────────────────────────


class TestNormalizeChannelData:
    def test_identity_resample(self):
        """Same timestamps in and out should return same values."""
        src_ts = np.linspace(0, 1, 61)
        values = np.sin(src_ts)
        result = normalize_channel_data(src_ts, values, src_ts)
        np.testing.assert_allclose(result, values, atol=1e-10)

    def test_upsample_linear(self):
        """Upsampling from 10 Hz → 60 Hz should interpolate smoothly."""
        src_ts = np.linspace(0, 1, 11)  # 10 Hz
        values = src_ts * 100.0  # linear ramp
        tgt_ts = np.linspace(0, 1, 61)  # 60 Hz
        result = normalize_channel_data(src_ts, values, tgt_ts)
        expected = tgt_ts * 100.0
        np.testing.assert_allclose(result, expected, atol=0.1)

    def test_downsample_linear(self):
        """Downsampling from 60 Hz → 10 Hz should preserve linear trend."""
        src_ts = np.linspace(0, 1, 61)  # 60 Hz
        values = src_ts * 200.0
        tgt_ts = np.linspace(0, 1, 11)  # 10 Hz
        result = normalize_channel_data(src_ts, values, tgt_ts)
        expected = tgt_ts * 200.0
        np.testing.assert_allclose(result, expected, atol=0.1)

    def test_discrete_nearest_neighbour(self):
        """Discrete channels should use nearest-neighbour, not linear."""
        src_ts = np.array([0.0, 1.0, 2.0, 3.0])
        values = np.array([1.0, 3.0, 5.0, 7.0])
        tgt_ts = np.array([0.0, 0.4, 0.6, 1.0, 1.5, 2.0, 2.9])
        result = normalize_channel_data(src_ts, values, tgt_ts, discrete=True)
        # Nearest-neighbour: 0.4 → 1, 0.6 → 3, 1.5 → 3 or 5, 2.9 → 7
        assert result[0] == 1.0
        assert result[3] == 3.0
        assert result[5] == 5.0
        assert result[6] == 7.0

    def test_empty_source(self):
        result = normalize_channel_data(
            np.array([]), np.array([]), np.linspace(0, 1, 10),
        )
        assert len(result) == 0

    def test_empty_target(self):
        result = normalize_channel_data(
            np.linspace(0, 1, 10), np.ones(10), np.array([]),
        )
        assert len(result) == 0

    def test_single_source_sample(self):
        """A single source sample should repeat for all targets."""
        result = normalize_channel_data(
            np.array([0.5]), np.array([42.0]), np.linspace(0, 1, 5),
        )
        np.testing.assert_allclose(result, 42.0)

    def test_extrapolation_clamps(self):
        """Values outside source range should clamp to first/last."""
        src_ts = np.array([1.0, 2.0, 3.0])
        values = np.array([10.0, 20.0, 30.0])
        tgt_ts = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        result = normalize_channel_data(src_ts, values, tgt_ts)
        assert result[0] == 10.0  # clamped to first
        assert result[4] == 30.0  # clamped to last


# ── normalize_frames ────────────────────────────────────────────────────────


class TestNormalizeFrames:
    def test_basic_60hz(self):
        """Normalise 30 Hz data to 60 Hz — frame count should roughly double."""
        frames = _make_frames(30, 1.0)
        result = normalize_frames(frames, target_rate_hz=60)

        assert isinstance(result, NormalizationResult)
        assert result.target_rate_hz == 60
        assert abs(result.original_rate_hz - 30.0) < 1.0
        # 1 second at 60 Hz → 61 samples (0.0, 0.0167, …, 1.0)
        assert len(result.frames) == 61
        assert "speed" in result.channel_names
        assert "rpm" in result.channel_names

    def test_downsample_60_to_10(self):
        """Normalise 60 Hz data to 10 Hz."""
        frames = _make_frames(60, 1.0)
        result = normalize_frames(frames, target_rate_hz=10)

        assert result.target_rate_hz == 10
        assert abs(result.original_rate_hz - 60.0) < 1.0
        assert len(result.frames) == 11  # 0.0, 0.1, …, 1.0

    def test_preserves_linear_ramp(self):
        """A linear ramp should be preserved exactly through normalisation."""
        frames = _make_frames(
            20, 1.0, channels={"ramp": lambda t: t * 100.0},
        )
        result = normalize_frames(frames, target_rate_hz=60)

        for frame in result.frames:
            expected = frame.ts * 100.0
            assert abs(frame.channels["ramp"] - expected) < 0.5

    def test_discrete_channel_stays_integer_like(self):
        """Gear channel should remain integer-like after normalisation."""
        frames = _make_frames(
            30, 1.0, channels={"gear": lambda t: float(int(t * 3) + 1)},
        )
        result = normalize_frames(frames, target_rate_hz=60)

        for frame in result.frames:
            gear = frame.channels["gear"]
            assert gear == float(int(gear)), f"Gear should be integer-like, got {gear}"

    def test_too_few_frames_raises(self):
        with pytest.raises(ValueError, match="at least 2 frames"):
            normalize_frames([TmuFrame(ts=0.0, channels={"x": 1.0})])

    def test_zero_rate_raises(self):
        frames = _make_frames(30, 0.1)
        with pytest.raises(ValueError, match="positive"):
            normalize_frames(frames, target_rate_hz=0)

    def test_negative_rate_raises(self):
        frames = _make_frames(30, 0.1)
        with pytest.raises(ValueError, match="positive"):
            normalize_frames(frames, target_rate_hz=-10)

    def test_result_repr(self):
        frames = _make_frames(30, 0.5)
        result = normalize_frames(frames, target_rate_hz=60)
        r = repr(result)
        assert "NormalizationResult" in r
        assert "target_rate_hz=60" in r

    def test_channels_with_missing_values(self):
        """Frames with partially-overlapping channel sets should work."""
        frames = [
            TmuFrame(ts=0.0, channels={"speed": 100.0}),
            TmuFrame(ts=0.5, channels={"speed": 150.0, "rpm": 5000.0}),
            TmuFrame(ts=1.0, channels={"speed": 200.0, "rpm": 6000.0}),
        ]
        result = normalize_frames(frames, target_rate_hz=10)
        assert "speed" in result.channel_names
        assert "rpm" in result.channel_names

    def test_uniform_timestamps_output(self):
        """Output timestamps should be uniformly spaced."""
        frames = _make_frames(30, 1.0)
        result = normalize_frames(frames, target_rate_hz=60)

        timestamps = [f.ts for f in result.frames]
        diffs = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
        expected_dt = 1.0 / 60
        for dt in diffs:
            assert abs(dt - expected_dt) < 1e-9


# ── TmuHeader sample_rate_hz fields ────────────────────────────────────────


class TestTmuHeaderSampleRate:
    def test_round_trip_with_sample_rates(self):
        hdr = TmuHeader(
            track="Spa",
            sample_rate_hz=60,
            original_sample_rate_hz=30.5,
        )
        d = hdr.to_dict()
        assert d["sample_rate_hz"] == 60
        assert d["original_sample_rate_hz"] == 30.5

        restored = TmuHeader.from_dict(d)
        assert restored.sample_rate_hz == 60
        assert restored.original_sample_rate_hz == 30.5

    def test_round_trip_without_sample_rates(self):
        """Omitting sample_rate fields should still work (backward compat)."""
        hdr = TmuHeader(track="Monza")
        d = hdr.to_dict()
        assert "sample_rate_hz" not in d
        assert "original_sample_rate_hz" not in d

        restored = TmuHeader.from_dict(d)
        assert restored.sample_rate_hz == 0
        assert restored.original_sample_rate_hz == 0.0

    def test_from_dict_ignores_unknown_as_extra(self):
        d = {"track": "LM", "sample_rate_hz": 60, "custom_key": "val"}
        hdr = TmuHeader.from_dict(d)
        assert hdr.sample_rate_hz == 60
        assert hdr.extra == {"custom_key": "val"}
