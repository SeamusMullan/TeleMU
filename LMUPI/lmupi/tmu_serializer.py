"""Binary serializer for LMU shared memory structs.

Converts LMU shared memory telemetry and scoring data into flat binary
frames suitable for writing to ``.tmu`` files.

Each frame contains a timestamp followed by the values of all configured
channels, packed according to their :class:`ChannelType`.
"""

from __future__ import annotations

import math
import struct

from lmupi.tmu_format import (
    CHANNEL_STRUCT_FMT,
    CHANNEL_TYPE_SIZE,
    ChannelDef,
    ChannelType,
)

# Kelvin → Celsius offset
_K2C = 273.15


def _speed_from_local_vel(vel) -> float:
    """Compute speed in km/h from local velocity vector (m/s)."""
    return math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2) * 3.6


# ── Default channel definitions ──────────────────────────

def default_channels() -> list[ChannelDef]:
    """Return the default set of telemetry channels to record.

    This maps relevant fields from ``LMUVehicleTelemetry`` and
    ``LMUVehicleScoring`` to named channels with appropriate units.
    """
    return [
        # Core driving inputs / outputs
        ChannelDef("Speed", ChannelType.FLOAT64, "km/h"),
        ChannelDef("RPM", ChannelType.FLOAT64, "rpm"),
        ChannelDef("Throttle", ChannelType.FLOAT64, "%"),
        ChannelDef("Brake", ChannelType.FLOAT64, "%"),
        ChannelDef("Steering", ChannelType.FLOAT64, "deg"),
        ChannelDef("Gear", ChannelType.INT32, ""),
        ChannelDef("Clutch", ChannelType.FLOAT64, "%"),
        # Engine
        ChannelDef("EngineWaterTemp", ChannelType.FLOAT64, "°C"),
        ChannelDef("EngineOilTemp", ChannelType.FLOAT64, "°C"),
        ChannelDef("EngineTorque", ChannelType.FLOAT64, "Nm"),
        ChannelDef("EngineMaxRPM", ChannelType.FLOAT64, "rpm"),
        # Fuel
        ChannelDef("Fuel", ChannelType.FLOAT64, "L"),
        ChannelDef("FuelCapacity", ChannelType.FLOAT64, "L"),
        # Tyre temperatures (center, Kelvin→Celsius)
        ChannelDef("TyreTempFL", ChannelType.FLOAT64, "°C"),
        ChannelDef("TyreTempFR", ChannelType.FLOAT64, "°C"),
        ChannelDef("TyreTempRL", ChannelType.FLOAT64, "°C"),
        ChannelDef("TyreTempRR", ChannelType.FLOAT64, "°C"),
        # Tyre pressures
        ChannelDef("TyrePressFL", ChannelType.FLOAT64, "kPa"),
        ChannelDef("TyrePressFR", ChannelType.FLOAT64, "kPa"),
        ChannelDef("TyrePressRL", ChannelType.FLOAT64, "kPa"),
        ChannelDef("TyrePressRR", ChannelType.FLOAT64, "kPa"),
        # Brake temperatures
        ChannelDef("BrakeTempFL", ChannelType.FLOAT64, "°C"),
        ChannelDef("BrakeTempFR", ChannelType.FLOAT64, "°C"),
        ChannelDef("BrakeTempRL", ChannelType.FLOAT64, "°C"),
        ChannelDef("BrakeTempRR", ChannelType.FLOAT64, "°C"),
        # Position
        ChannelDef("PosX", ChannelType.FLOAT64, "m"),
        ChannelDef("PosY", ChannelType.FLOAT64, "m"),
        ChannelDef("PosZ", ChannelType.FLOAT64, "m"),
        # Velocity
        ChannelDef("VelX", ChannelType.FLOAT64, "m/s"),
        ChannelDef("VelY", ChannelType.FLOAT64, "m/s"),
        ChannelDef("VelZ", ChannelType.FLOAT64, "m/s"),
        # Acceleration
        ChannelDef("AccelX", ChannelType.FLOAT64, "m/s²"),
        ChannelDef("AccelY", ChannelType.FLOAT64, "m/s²"),
        ChannelDef("AccelZ", ChannelType.FLOAT64, "m/s²"),
        # Ride height
        ChannelDef("FrontRideHeight", ChannelType.FLOAT64, "m"),
        ChannelDef("RearRideHeight", ChannelType.FLOAT64, "m"),
        # Aero
        ChannelDef("Drag", ChannelType.FLOAT64, ""),
        ChannelDef("FrontDownforce", ChannelType.FLOAT64, ""),
        ChannelDef("RearDownforce", ChannelType.FLOAT64, ""),
        # Scoring (LapNumber = mTotalLaps + 1, i.e. current 1-indexed lap)
        ChannelDef("LapNumber", ChannelType.INT32, ""),
        ChannelDef("LapDist", ChannelType.FLOAT64, "m"),
        ChannelDef("CurrentSector", ChannelType.INT32, ""),
        ChannelDef("InPits", ChannelType.BOOL, ""),
        # Lap times
        ChannelDef("LastLapTime", ChannelType.FLOAT64, "s"),
        ChannelDef("BestLapTime", ChannelType.FLOAT64, "s"),
        # Session time
        ChannelDef("ElapsedTime", ChannelType.FLOAT64, "s"),
        ChannelDef("DeltaTime", ChannelType.FLOAT64, "s"),
    ]


# ── Serializer ────────────────────────────────────────────

class TelemetrySerializer:
    """Converts shared memory data into flat binary frames.

    Args:
        channels: List of channel definitions to serialize. If ``None``,
            uses :func:`default_channels`.
    """

    def __init__(self, channels: list[ChannelDef] | None = None) -> None:
        self._channels = channels if channels is not None else default_channels()
        self._compute_offsets()
        # Build the struct format string: timestamp (double) + all channels
        fmt_parts = ["<d"]  # little-endian, timestamp double
        for ch in self._channels:
            fmt_parts.append(CHANNEL_STRUCT_FMT[ch.type_code])
        self._fmt = "".join(fmt_parts)
        self._frame_size = struct.calcsize(self._fmt)

    def _compute_offsets(self) -> None:
        """Compute byte offsets for each channel within a frame."""
        offset = 8  # after timestamp (double = 8 bytes)
        for ch in self._channels:
            ch.byte_offset = offset
            offset += CHANNEL_TYPE_SIZE[ch.type_code]

    @property
    def channels(self) -> list[ChannelDef]:
        return self._channels

    @property
    def frame_size(self) -> int:
        return self._frame_size

    def serialize_frame(self, timestamp: float, vt, vs) -> bytes:
        """Serialize one telemetry frame from shared memory structs.

        Args:
            timestamp: Session timestamp in seconds.
            vt: ``LMUVehicleTelemetry`` struct (player vehicle).
            vs: ``LMUVehicleScoring`` struct (player vehicle).

        Returns:
            Packed binary frame bytes.
        """
        values = self._extract_values(timestamp, vt, vs)
        return struct.pack(self._fmt, *values)

    def _extract_values(self, timestamp: float, vt, vs) -> list:
        """Extract channel values from shared memory structs.

        Handles type conversions (Kelvin→Celsius, etc.) as described
        in issue #2 requirements.
        """
        speed = _speed_from_local_vel(vt.mLocalVel)

        values: list = [timestamp]
        for ch in self._channels:
            values.append(self._read_channel(ch.name, vt, vs, speed))
        return values

    def _read_channel(self, name: str, vt, vs, speed: float):
        """Read a single channel value from the shared memory structs."""
        # fmt: off
        readers = {
            "Speed":            lambda: speed,
            "RPM":              lambda: vt.mEngineRPM,
            "Throttle":         lambda: vt.mUnfilteredThrottle * 100.0,
            "Brake":            lambda: vt.mUnfilteredBrake * 100.0,
            "Steering":         lambda: vt.mUnfilteredSteering * vt.mPhysicalSteeringWheelRange,
            "Gear":             lambda: vt.mGear,
            "Clutch":           lambda: vt.mUnfilteredClutch * 100.0,
            "EngineWaterTemp":  lambda: vt.mEngineWaterTemp,
            "EngineOilTemp":    lambda: vt.mEngineOilTemp,
            "EngineTorque":     lambda: vt.mEngineTorque,
            "EngineMaxRPM":     lambda: vt.mEngineMaxRPM,
            "Fuel":             lambda: vt.mFuel,
            "FuelCapacity":     lambda: vt.mFuelCapacity,
            # Tyre temps (center index=1, Kelvin → Celsius)
            "TyreTempFL":       lambda: vt.mWheels[0].mTemperature[1] - _K2C,
            "TyreTempFR":       lambda: vt.mWheels[1].mTemperature[1] - _K2C,
            "TyreTempRL":       lambda: vt.mWheels[2].mTemperature[1] - _K2C,
            "TyreTempRR":       lambda: vt.mWheels[3].mTemperature[1] - _K2C,
            # Tyre pressures
            "TyrePressFL":      lambda: vt.mWheels[0].mPressure,
            "TyrePressFR":      lambda: vt.mWheels[1].mPressure,
            "TyrePressRL":      lambda: vt.mWheels[2].mPressure,
            "TyrePressRR":      lambda: vt.mWheels[3].mPressure,
            # Brake temps (Celsius)
            "BrakeTempFL":      lambda: vt.mWheels[0].mBrakeTemp,
            "BrakeTempFR":      lambda: vt.mWheels[1].mBrakeTemp,
            "BrakeTempRL":      lambda: vt.mWheels[2].mBrakeTemp,
            "BrakeTempRR":      lambda: vt.mWheels[3].mBrakeTemp,
            # Position
            "PosX":             lambda: vt.mPos.x,
            "PosY":             lambda: vt.mPos.y,
            "PosZ":             lambda: vt.mPos.z,
            # Velocity
            "VelX":             lambda: vt.mLocalVel.x,
            "VelY":             lambda: vt.mLocalVel.y,
            "VelZ":             lambda: vt.mLocalVel.z,
            # Acceleration
            "AccelX":           lambda: vt.mLocalAccel.x,
            "AccelY":           lambda: vt.mLocalAccel.y,
            "AccelZ":           lambda: vt.mLocalAccel.z,
            # Ride height
            "FrontRideHeight":  lambda: vt.mFrontRideHeight,
            "RearRideHeight":   lambda: vt.mRearRideHeight,
            # Aero
            "Drag":             lambda: vt.mDrag,
            "FrontDownforce":   lambda: vt.mFrontDownforce,
            "RearDownforce":    lambda: vt.mRearDownforce,
            # Scoring
            "LapNumber":        lambda: vs.mTotalLaps + 1,
            "LapDist":          lambda: vs.mLapDist,
            "CurrentSector":    lambda: vt.mCurrentSector,
            "InPits":           lambda: bool(vs.mInPits),
            # Lap times
            "LastLapTime":      lambda: vs.mLastLapTime,
            "BestLapTime":      lambda: vs.mBestLapTime,
            # Session time
            "ElapsedTime":      lambda: vt.mElapsedTime,
            "DeltaTime":        lambda: vt.mDeltaTime,
        }
        # fmt: on
        reader = readers.get(name)
        if reader is None:
            return 0
        return reader()
