"""Normalize telemetry sample rates across channels.

Resamples telemetry frames so every channel is aligned to a uniform time grid.

Supports:
- **Upsampling** (interpolation) when original data has a lower rate than the target.
- **Downsampling** (decimation with averaging) when original data has a higher rate.
- Configurable target rate (default 60 Hz).
- Metadata tracking of both original and normalized sample rates.

Usage::

    from telemu.recording.normalizer import normalize_frames

    normalized = normalize_frames(frames, target_rate_hz=60)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from telemu.recording.tmu_ndjson import TmuFrame

# Channels that represent discrete / categorical values and should be held
# constant (nearest-neighbour) rather than linearly interpolated.
_DISCRETE_CHANNELS: frozenset[str] = frozenset({
    "gear",
    "lap_number",
    "current_sector",
    "place",
    "total_laps",
    "flag",
    "pit_state",
    "num_pitstops",
    "num_penalties",
    "finish_status",
    "boost_motor_state",
    "speed_limiter",
    # Booleans
    "overheating",
    "headlights",
    "in_pits",
    "drs",
})


class NormalizationResult:
    """Container for normalized telemetry data with metadata.

    Attributes
    ----------
    frames : list[TmuFrame]
        Resampled telemetry frames on a uniform time grid.
    target_rate_hz : int
        The sample rate the data was normalised to.
    original_rate_hz : float
        Estimated sample rate of the *input* data.
    channel_names : list[str]
        Channel names present in the normalised output.
    """

    __slots__ = ("frames", "target_rate_hz", "original_rate_hz", "channel_names")

    def __init__(
        self,
        frames: list[TmuFrame],
        target_rate_hz: int,
        original_rate_hz: float,
        channel_names: list[str],
    ) -> None:
        self.frames = frames
        self.target_rate_hz = target_rate_hz
        self.original_rate_hz = original_rate_hz
        self.channel_names = channel_names

    def __repr__(self) -> str:
        return (
            f"NormalizationResult(frames={len(self.frames)}, "
            f"target_rate_hz={self.target_rate_hz}, "
            f"original_rate_hz={self.original_rate_hz:.1f})"
        )


def estimate_sample_rate(timestamps: NDArray[np.float64]) -> float:
    """Estimate the sample rate from a sequence of timestamps.

    Returns the *median*-based rate (1 / median_dt) to be robust against
    occasional jitter or dropped frames.
    """
    if len(timestamps) < 2:
        return 0.0
    diffs = np.diff(timestamps)
    median_dt = float(np.median(diffs))
    if median_dt <= 0:
        return 0.0
    return 1.0 / median_dt


def normalize_channel_data(
    source_ts: NDArray[np.float64],
    values: NDArray[np.float64],
    target_ts: NDArray[np.float64],
    *,
    discrete: bool = False,
) -> NDArray[np.float64]:
    """Resample a single channel onto *target_ts*.

    Parameters
    ----------
    source_ts : original timestamps (must be monotonically non-decreasing).
    values : channel values corresponding to *source_ts*.
    target_ts : desired output timestamps.
    discrete : if ``True``, use nearest-neighbour interpolation (for gear,
        flags, …); otherwise use linear interpolation.

    Returns
    -------
    numpy array of resampled values aligned to *target_ts*.
    """
    if len(source_ts) == 0 or len(target_ts) == 0:
        return np.empty(0, dtype=np.float64)

    if len(source_ts) == 1:
        # Single sample — repeat for every target timestamp
        return np.full(len(target_ts), values[0], dtype=np.float64)

    kind = "nearest" if discrete else "linear"
    interpolator = interp1d(
        source_ts,
        values,
        kind=kind,
        bounds_error=False,
        fill_value=(float(values[0]), float(values[-1])),
    )
    return interpolator(target_ts).astype(np.float64)


def normalize_frames(
    frames: list[TmuFrame],
    target_rate_hz: int = 60,
) -> NormalizationResult:
    """Resample telemetry frames onto a uniform time grid.

    Parameters
    ----------
    frames : input frames (potentially irregular or multi-rate).
    target_rate_hz : desired output sample rate in Hz (must be > 0).

    Returns
    -------
    NormalizationResult with the resampled frames and metadata.

    Raises
    ------
    ValueError
        If *target_rate_hz* is not positive or there are fewer than 2 frames.
    """
    if target_rate_hz <= 0:
        raise ValueError(f"target_rate_hz must be positive, got {target_rate_hz}")
    if len(frames) < 2:
        raise ValueError(
            f"Need at least 2 frames to normalise, got {len(frames)}"
        )

    # ── Collect source timestamps and discover channels ────────────────
    source_ts = np.array([f.ts for f in frames], dtype=np.float64)

    all_channels: list[str] = []
    seen: set[str] = set()
    for f in frames:
        for ch in f.channels:
            if ch not in seen:
                all_channels.append(ch)
                seen.add(ch)

    original_rate = estimate_sample_rate(source_ts)

    # ── Build uniform target time grid ─────────────────────────────────
    t_start = float(source_ts[0])
    t_end = float(source_ts[-1])
    dt = 1.0 / target_rate_hz
    target_ts = np.arange(t_start, t_end + dt * 0.5, dt, dtype=np.float64)
    # Clip to not overshoot past original range
    target_ts = target_ts[target_ts <= t_end + 1e-9]

    # ── Resample each channel ──────────────────────────────────────────
    channel_arrays: dict[str, NDArray[np.float64]] = {}
    for ch_name in all_channels:
        ch_values = np.array(
            [f.channels.get(ch_name, np.nan) for f in frames],
            dtype=np.float64,
        )
        discrete = ch_name in _DISCRETE_CHANNELS
        channel_arrays[ch_name] = normalize_channel_data(
            source_ts, ch_values, target_ts, discrete=discrete,
        )

    # ── Reconstruct frames ─────────────────────────────────────────────
    result_frames: list[TmuFrame] = []
    for i, ts_val in enumerate(target_ts):
        channels: dict[str, float] = {}
        for ch_name in all_channels:
            val = float(channel_arrays[ch_name][i])
            if not np.isnan(val):
                channels[ch_name] = val
        result_frames.append(TmuFrame(ts=float(ts_val), channels=channels))

    return NormalizationResult(
        frames=result_frames,
        target_rate_hz=target_rate_hz,
        original_rate_hz=original_rate,
        channel_names=list(all_channels),
    )
