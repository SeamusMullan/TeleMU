"""Binary frame serializer for .tmu recording.

Converts LMU shared memory structs into flat binary frames using
``struct.pack``.  Supports configurable channel selection so callers
can record a subset of available data.

Example::

    from telemu.recording.serializer import FrameSerializer

    ser = FrameSerializer(["speed", "rpm", "throttle"])
    frame = ser.serialize(timestamp, vehicle_telemetry, vehicle_scoring)
    values = ser.deserialize(frame)
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from typing import Any

from telemu.recording.channels import ALL_CHANNELS, DEFAULT_CHANNELS, ChannelDef


class FrameSerializer:
    """Packs/unpacks selected telemetry channels into flat binary frames.

    Parameters
    ----------
    channels:
        Ordered list of channel names to include.  ``None`` uses
        :data:`~telemu.recording.channels.DEFAULT_CHANNELS`.

    Raises
    ------
    ValueError
        If *channels* is empty or contains unknown channel names.
    """

    def __init__(self, channels: Sequence[str] | None = None) -> None:
        names = list(channels) if channels is not None else list(DEFAULT_CHANNELS)
        if not names:
            raise ValueError("At least one channel must be selected")

        unknown = [n for n in names if n not in ALL_CHANNELS]
        if unknown:
            raise ValueError(f"Unknown channel(s): {', '.join(unknown)}")

        self._defs: list[ChannelDef] = [ALL_CHANNELS[n] for n in names]
        # Little-endian: timestamp (float64) followed by each channel
        self._fmt = "<d" + "".join(ch.fmt for ch in self._defs)
        self._size = struct.calcsize(self._fmt)

    # ── Public API ────────────────────────────────────────────────────

    def serialize(
        self,
        timestamp: float,
        telemetry: Any,
        scoring: Any,
    ) -> bytes:
        """Pack *timestamp* and channel values into a binary frame.

        Parameters
        ----------
        timestamp:
            Frame timestamp (typically ``mElapsedTime``).
        telemetry:
            An ``LMUVehicleTelemetry`` instance (or compatible object).
        scoring:
            An ``LMUVehicleScoring`` instance (or compatible object).

        Returns
        -------
        bytes
            Flat binary frame of :attr:`frame_size` bytes.
        """
        values: list[int | float | bool] = [timestamp]
        for ch in self._defs:
            values.append(ch.extract(telemetry, scoring))
        return struct.pack(self._fmt, *values)

    def deserialize(self, data: bytes) -> dict[str, float | int | bool]:
        """Unpack a binary frame back into a ``{channel: value}`` dict.

        The returned dict always contains a ``"timestamp"`` key plus one
        entry per selected channel.

        Raises
        ------
        struct.error
            If *data* is not exactly :attr:`frame_size` bytes.
        """
        values = struct.unpack(self._fmt, data)
        result: dict[str, float | int | bool] = {"timestamp": values[0]}
        for i, ch in enumerate(self._defs):
            result[ch.name] = values[i + 1]
        return result

    # ── Properties ────────────────────────────────────────────────────

    @property
    def frame_size(self) -> int:
        """Size of one serialized frame in bytes."""
        return self._size

    @property
    def format_string(self) -> str:
        """``struct`` format string used for packing."""
        return self._fmt

    @property
    def channel_names(self) -> list[str]:
        """Ordered list of channel names in each frame."""
        return [ch.name for ch in self._defs]

    @property
    def channel_defs(self) -> list[ChannelDef]:
        """Ordered list of :class:`ChannelDef` objects in each frame."""
        return list(self._defs)
