"""Delta compression for slowly-changing telemetry channels.

Encodes telemetry channel values as deltas from previous frames. Channels that
change slowly (e.g. fuel level, tyre temps) produce many near-zero deltas which
compress significantly better under LZ4/zstd than raw absolute values.

The encoder tracks per-channel state and emits absolute values for new channels,
zero for unchanged channels (within a configurable threshold), and deltas
otherwise. The decoder transparently reconstructs absolute values.

Typical improvement: 20-40% additional compression on top of zstd for telemetry
data with slowly-changing channels like fuel, tyre temperatures, and gear.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import zstandard

# ── Default per-channel thresholds ────────────────────────────────────────────
# Deltas at or below these values are stored as 0.0 (no change).
# Channels not listed use DEFAULT_THRESHOLD.

DEFAULT_THRESHOLDS: dict[str, float] = {
    "fuel": 0.001,
    "fuel_capacity": 0.0,
    "rpm_max": 0.0,
    "gear": 0.0,
    "tyre_fl": 0.05,
    "tyre_fr": 0.05,
    "tyre_rl": 0.05,
    "tyre_rr": 0.05,
}

DEFAULT_THRESHOLD: float = 0.0


# ── Data structures ──────────────────────────────────────────────────────────


@dataclass
class DeltaFrame:
    """A delta-encoded telemetry frame.

    Attributes:
        values: Channel values — absolute for channels in *absolute_channels*,
            deltas for all others (0.0 means no change).
        absolute_channels: Names of channels stored as absolute values in this
            frame (typically only the first frame for each channel).
    """

    values: dict[str, float] = field(default_factory=dict)
    absolute_channels: frozenset[str] = field(default_factory=frozenset)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "v": self.values,
            "abs": sorted(self.absolute_channels),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeltaFrame:
        """Deserialize from a dict produced by :meth:`to_dict`."""
        return cls(
            values=data["v"],
            absolute_channels=frozenset(data["abs"]),
        )

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes."""
        return json.dumps(self.to_dict(), separators=(",", ":")).encode()

    @classmethod
    def from_bytes(cls, raw: bytes) -> DeltaFrame:
        """Deserialize from bytes produced by :meth:`to_bytes`."""
        return cls.from_dict(json.loads(raw))


# ── Encoder ───────────────────────────────────────────────────────────────────


class DeltaEncoder:
    """Encodes telemetry channel values using delta compression.

    For each channel the encoder tracks the last value that was communicated to
    the decoder (i.e. the last value that was either sent as an absolute or as a
    non-zero delta).  When the difference between the current value and the
    tracked value is at or below the configured threshold the encoder emits 0.0,
    which compresses extremely well.

    Parameters:
        thresholds: Per-channel delta thresholds. Deltas with ``abs(delta) <=
            threshold`` are stored as 0.0.  Defaults to :data:`DEFAULT_THRESHOLDS`.
        default_threshold: Threshold for channels not in *thresholds*.
            Defaults to :data:`DEFAULT_THRESHOLD`.
    """

    def __init__(
        self,
        thresholds: dict[str, float] | None = None,
        default_threshold: float | None = None,
    ) -> None:
        self._thresholds = (
            thresholds if thresholds is not None else DEFAULT_THRESHOLDS.copy()
        )
        self._default_threshold = (
            default_threshold if default_threshold is not None else DEFAULT_THRESHOLD
        )
        self._prev: dict[str, float] = {}

    def encode(self, channels: dict[str, float]) -> DeltaFrame:
        """Delta-encode a set of channel values.

        Returns a :class:`DeltaFrame` with deltas (or absolute values for
        channels seen for the first time).
        """
        values: dict[str, float] = {}
        absolute: set[str] = set()

        for name, value in channels.items():
            if name not in self._prev:
                # First occurrence — store absolute value.
                values[name] = value
                absolute.add(name)
                self._prev[name] = value
            else:
                delta = value - self._prev[name]
                threshold = self._thresholds.get(name, self._default_threshold)
                if abs(delta) <= threshold:
                    # Below threshold — treat as unchanged.
                    values[name] = 0.0
                else:
                    values[name] = delta
                    self._prev[name] = value

        return DeltaFrame(values=values, absolute_channels=frozenset(absolute))

    def reset(self) -> None:
        """Reset encoder state (e.g. at the start of a new recording)."""
        self._prev.clear()


# ── Decoder ───────────────────────────────────────────────────────────────────


class DeltaDecoder:
    """Reconstructs absolute channel values from delta-encoded frames.

    Transparent to consumers — the output is identical to the original channel
    dict (within floating-point precision and the configured threshold).
    """

    def __init__(self) -> None:
        self._prev: dict[str, float] = {}

    def decode(self, frame: DeltaFrame) -> dict[str, float]:
        """Decode a :class:`DeltaFrame` back to absolute channel values."""
        result: dict[str, float] = {}

        for name, value in frame.values.items():
            if name in frame.absolute_channels:
                result[name] = value
            else:
                result[name] = self._prev.get(name, 0.0) + value
            self._prev[name] = result[name]

        return result

    def reset(self) -> None:
        """Reset decoder state (e.g. at the start of a new playback)."""
        self._prev.clear()


# ── Convenience: combined delta + zstd ────────────────────────────────────────


def compress_frame(
    channels: dict[str, float],
    encoder: DeltaEncoder,
    *,
    zstd_level: int = 3,
) -> bytes:
    """Delta-encode *channels* and compress the result with zstd.

    Suitable for both recording (writing to ``.tmu`` files) and streaming
    (sending over the network).
    """
    frame = encoder.encode(channels)
    raw = frame.to_bytes()
    return zstandard.ZstdCompressor(level=zstd_level).compress(raw)


def decompress_frame(
    data: bytes,
    decoder: DeltaDecoder,
) -> dict[str, float]:
    """Decompress *data* and delta-decode it back to absolute channel values."""
    raw = zstandard.ZstdDecompressor().decompress(data)
    frame = DeltaFrame.from_bytes(raw)
    return decoder.decode(frame)
