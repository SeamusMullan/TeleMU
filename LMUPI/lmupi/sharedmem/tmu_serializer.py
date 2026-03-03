"""Binary serializer for LMU shared memory structs into .tmu frame format.

Converts ``LMUVehicleTelemetry`` and ``LMUVehicleScoring`` data into compact
binary frames suitable for recording telemetry sessions.

Frame layout
------------
Each frame is a flat binary record consisting of:

1. **Timestamp** — ``double`` (8 bytes, little-endian)
2. **Channel values** — packed according to the channel definition table

The channel definition table describes every recordable channel:
name, data-type code, unit string, and an optional extraction/transform
function that pulls a value from the live structs and applies any
necessary unit conversion (e.g. Kelvin → Celsius).

Usage
-----
::

    ser = TMUSerializer()                          # all channels
    ser = TMUSerializer(channels=["speed", ...])   # subset

    header = ser.encode_header(track="Monza", car="Porsche 963",
                               driver="Player", sample_rate=60.0)
    frame  = ser.encode_frame(telemetry, scoring)

Wire types
----------
=====  ===========  ============  ==================
Code   Python type  ``struct``    Size (bytes)
=====  ===========  ============  ==================
``d``  float64      ``<d``        8
``f``  float32      ``<f``        4
``i``  int32        ``<i``        4
``B``  uint8        ``<B``        1
``?``  bool         ``<?``        1
=====  ===========  ============  ==================

All multi-byte values are **little-endian**.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAGIC = b"TMU\x00"           # 4-byte magic identifier
FORMAT_VERSION: int = 1       # format revision
KELVIN_OFFSET: float = 273.15


# ---------------------------------------------------------------------------
# Channel descriptor
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ChannelDescriptor:
    """Describes one recordable telemetry channel.

    Attributes:
        name:      Human-readable channel name (unique key).
        type_code: ``struct`` format character (``d``, ``f``, ``i``, ``B``, ``?``).
        unit:      Physical unit string (for display / documentation).
        extractor: Callable ``(telemetry, scoring) -> value`` that reads from
                   the live ctypes structs and returns the channel value,
                   applying any necessary unit conversion.
    """

    name: str
    type_code: str
    unit: str
    extractor: Callable[[Any, Any], int | float | bool] | None = None


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _speed_from_local_vel(vel) -> float:
    """Compute speed in km/h from a local-velocity vector (m/s)."""
    return math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2) * 3.6


def _kelvin_to_celsius(k: float) -> float:
    return k - KELVIN_OFFSET


def _rad_to_deg(r: float) -> float:
    return math.degrees(r)


# ---------------------------------------------------------------------------
# Default channel catalogue
# ---------------------------------------------------------------------------
# Each entry is ``(name, type_code, unit, extractor)``.
# ``t`` = telemetry (LMUVehicleTelemetry), ``s`` = scoring (LMUVehicleScoring).

_CHANNEL_DEFS: list[tuple[str, str, str, Callable]] = [
    # -- identifiers / timing --
    ("elapsed_time",        "d", "s",     lambda t, s: t.mElapsedTime),
    ("delta_time",          "d", "s",     lambda t, s: t.mDeltaTime),
    ("lap_number",          "i", "",      lambda t, s: t.mLapNumber),
    ("lap_start_et",        "d", "s",     lambda t, s: t.mLapStartET),
    ("current_sector",      "i", "",      lambda t, s: t.mCurrentSector),

    # -- position --
    ("pos_x",               "d", "m",     lambda t, s: t.mPos.x),
    ("pos_y",               "d", "m",     lambda t, s: t.mPos.y),
    ("pos_z",               "d", "m",     lambda t, s: t.mPos.z),

    # -- velocity --
    ("speed",               "d", "km/h",  lambda t, s: _speed_from_local_vel(t.mLocalVel)),
    ("local_vel_x",         "d", "m/s",   lambda t, s: t.mLocalVel.x),
    ("local_vel_y",         "d", "m/s",   lambda t, s: t.mLocalVel.y),
    ("local_vel_z",         "d", "m/s",   lambda t, s: t.mLocalVel.z),

    # -- acceleration --
    ("local_accel_x",       "d", "m/s²",  lambda t, s: t.mLocalAccel.x),
    ("local_accel_y",       "d", "m/s²",  lambda t, s: t.mLocalAccel.y),
    ("local_accel_z",       "d", "m/s²",  lambda t, s: t.mLocalAccel.z),

    # -- rotation (radians/sec → degrees/sec) --
    ("local_rot_x",         "d", "°/s",   lambda t, s: _rad_to_deg(t.mLocalRot.x)),
    ("local_rot_y",         "d", "°/s",   lambda t, s: _rad_to_deg(t.mLocalRot.y)),
    ("local_rot_z",         "d", "°/s",   lambda t, s: _rad_to_deg(t.mLocalRot.z)),

    # -- rotational acceleration (radians/sec² → degrees/sec²) --
    ("local_rot_accel_x",   "d", "°/s²",  lambda t, s: _rad_to_deg(t.mLocalRotAccel.x)),
    ("local_rot_accel_y",   "d", "°/s²",  lambda t, s: _rad_to_deg(t.mLocalRotAccel.y)),
    ("local_rot_accel_z",   "d", "°/s²",  lambda t, s: _rad_to_deg(t.mLocalRotAccel.z)),

    # -- driver inputs --
    ("throttle",            "d", "%",     lambda t, s: t.mUnfilteredThrottle * 100.0),
    ("brake",               "d", "%",     lambda t, s: t.mUnfilteredBrake * 100.0),
    ("steering",            "d", "°",     lambda t, s: t.mUnfilteredSteering * t.mPhysicalSteeringWheelRange),
    ("clutch",              "d", "%",     lambda t, s: t.mUnfilteredClutch * 100.0),
    ("filtered_throttle",   "d", "%",     lambda t, s: t.mFilteredThrottle * 100.0),
    ("filtered_brake",      "d", "%",     lambda t, s: t.mFilteredBrake * 100.0),
    ("filtered_steering",   "d", "°",     lambda t, s: t.mFilteredSteering * t.mPhysicalSteeringWheelRange),
    ("filtered_clutch",     "d", "%",     lambda t, s: t.mFilteredClutch * 100.0),
    ("steering_torque",     "d", "Nm",    lambda t, s: t.mSteeringShaftTorque),

    # -- drivetrain --
    ("gear",                "i", "",      lambda t, s: t.mGear),
    ("engine_rpm",          "d", "rpm",   lambda t, s: t.mEngineRPM),
    ("engine_max_rpm",      "d", "rpm",   lambda t, s: t.mEngineMaxRPM),
    ("clutch_rpm",          "d", "rpm",   lambda t, s: t.mClutchRPM),
    ("engine_torque",       "d", "Nm",    lambda t, s: t.mEngineTorque),
    ("max_gears",           "B", "",      lambda t, s: t.mMaxGears),

    # -- temperatures (already Celsius in struct) --
    ("engine_water_temp",   "d", "°C",    lambda t, s: t.mEngineWaterTemp),
    ("engine_oil_temp",     "d", "°C",    lambda t, s: t.mEngineOilTemp),

    # -- fuel --
    ("fuel",                "d", "L",     lambda t, s: t.mFuel),
    ("fuel_capacity",       "d", "L",     lambda t, s: t.mFuelCapacity),

    # -- aero / ride --
    ("front_downforce",     "d", "N",     lambda t, s: t.mFrontDownforce),
    ("rear_downforce",      "d", "N",     lambda t, s: t.mRearDownforce),
    ("drag",                "d", "N",     lambda t, s: t.mDrag),
    ("front_ride_height",   "d", "m",     lambda t, s: t.mFrontRideHeight),
    ("rear_ride_height",    "d", "m",     lambda t, s: t.mRearRideHeight),
    ("front_wing_height",   "d", "m",     lambda t, s: t.mFrontWingHeight),
    ("front_3rd_deflection","d", "m",     lambda t, s: t.mFront3rdDeflection),
    ("rear_3rd_deflection", "d", "m",     lambda t, s: t.mRear3rdDeflection),
    ("rear_brake_bias",     "d", "",      lambda t, s: t.mRearBrakeBias),

    # -- turbo / hybrid --
    ("turbo_boost_pressure",         "d", "kPa",  lambda t, s: t.mTurboBoostPressure),
    ("battery_charge",               "d", "",     lambda t, s: t.mBatteryChargeFraction),
    ("electric_boost_motor_torque",  "d", "Nm",   lambda t, s: t.mElectricBoostMotorTorque),
    ("electric_boost_motor_rpm",     "d", "rpm",  lambda t, s: t.mElectricBoostMotorRPM),
    ("electric_boost_motor_temp",    "d", "°C",   lambda t, s: t.mElectricBoostMotorTemperature),
    ("electric_boost_water_temp",    "d", "°C",   lambda t, s: t.mElectricBoostWaterTemperature),
    ("electric_boost_motor_state",   "B", "",     lambda t, s: t.mElectricBoostMotorState),

    # -- damage / status --
    ("last_impact_magnitude",  "d", "",   lambda t, s: t.mLastImpactMagnitude),
    ("overheating",            "?", "",   lambda t, s: bool(t.mOverheating)),
    ("detached",               "?", "",   lambda t, s: bool(t.mDetached)),
    ("headlights",             "?", "",   lambda t, s: bool(t.mHeadlights)),
    ("speed_limiter",          "B", "",   lambda t, s: t.mSpeedLimiter),

    # -- delta --
    ("delta_best",             "d", "s",  lambda t, s: t.mDeltaBest),

    # ---- per-wheel channels (FL / FR / RL / RR) ----
    # suspension
    ("susp_defl_fl",        "d", "m",     lambda t, s: t.mWheels[0].mSuspensionDeflection),
    ("susp_defl_fr",        "d", "m",     lambda t, s: t.mWheels[1].mSuspensionDeflection),
    ("susp_defl_rl",        "d", "m",     lambda t, s: t.mWheels[2].mSuspensionDeflection),
    ("susp_defl_rr",        "d", "m",     lambda t, s: t.mWheels[3].mSuspensionDeflection),
    ("ride_height_fl",      "d", "m",     lambda t, s: t.mWheels[0].mRideHeight),
    ("ride_height_fr",      "d", "m",     lambda t, s: t.mWheels[1].mRideHeight),
    ("ride_height_rl",      "d", "m",     lambda t, s: t.mWheels[2].mRideHeight),
    ("ride_height_rr",      "d", "m",     lambda t, s: t.mWheels[3].mRideHeight),
    ("susp_force_fl",       "d", "N",     lambda t, s: t.mWheels[0].mSuspForce),
    ("susp_force_fr",       "d", "N",     lambda t, s: t.mWheels[1].mSuspForce),
    ("susp_force_rl",       "d", "N",     lambda t, s: t.mWheels[2].mSuspForce),
    ("susp_force_rr",       "d", "N",     lambda t, s: t.mWheels[3].mSuspForce),

    # brakes (already Celsius in struct)
    ("brake_temp_fl",       "d", "°C",    lambda t, s: t.mWheels[0].mBrakeTemp),
    ("brake_temp_fr",       "d", "°C",    lambda t, s: t.mWheels[1].mBrakeTemp),
    ("brake_temp_rl",       "d", "°C",    lambda t, s: t.mWheels[2].mBrakeTemp),
    ("brake_temp_rr",       "d", "°C",    lambda t, s: t.mWheels[3].mBrakeTemp),
    ("brake_pressure_fl",   "d", "",      lambda t, s: t.mWheels[0].mBrakePressure),
    ("brake_pressure_fr",   "d", "",      lambda t, s: t.mWheels[1].mBrakePressure),
    ("brake_pressure_rl",   "d", "",      lambda t, s: t.mWheels[2].mBrakePressure),
    ("brake_pressure_rr",   "d", "",      lambda t, s: t.mWheels[3].mBrakePressure),

    # tire temperature (Kelvin → Celsius, centre element)
    ("tire_temp_fl",        "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[0].mTemperature[1])),
    ("tire_temp_fr",        "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[1].mTemperature[1])),
    ("tire_temp_rl",        "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[2].mTemperature[1])),
    ("tire_temp_rr",        "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[3].mTemperature[1])),

    # tire temperature — left / right edges (Kelvin → Celsius)
    ("tire_temp_fl_l",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[0].mTemperature[0])),
    ("tire_temp_fl_r",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[0].mTemperature[2])),
    ("tire_temp_fr_l",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[1].mTemperature[0])),
    ("tire_temp_fr_r",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[1].mTemperature[2])),
    ("tire_temp_rl_l",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[2].mTemperature[0])),
    ("tire_temp_rl_r",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[2].mTemperature[2])),
    ("tire_temp_rr_l",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[3].mTemperature[0])),
    ("tire_temp_rr_r",      "d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[3].mTemperature[2])),

    # tire carcass temperature (Kelvin → Celsius)
    ("tire_carcass_temp_fl","d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[0].mTireCarcassTemperature)),
    ("tire_carcass_temp_fr","d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[1].mTireCarcassTemperature)),
    ("tire_carcass_temp_rl","d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[2].mTireCarcassTemperature)),
    ("tire_carcass_temp_rr","d", "°C",    lambda t, s: _kelvin_to_celsius(t.mWheels[3].mTireCarcassTemperature)),

    # tire pressure
    ("tire_pressure_fl",    "d", "kPa",   lambda t, s: t.mWheels[0].mPressure),
    ("tire_pressure_fr",    "d", "kPa",   lambda t, s: t.mWheels[1].mPressure),
    ("tire_pressure_rl",    "d", "kPa",   lambda t, s: t.mWheels[2].mPressure),
    ("tire_pressure_rr",    "d", "kPa",   lambda t, s: t.mWheels[3].mPressure),

    # tire wear
    ("tire_wear_fl",        "d", "",      lambda t, s: t.mWheels[0].mWear),
    ("tire_wear_fr",        "d", "",      lambda t, s: t.mWheels[1].mWear),
    ("tire_wear_rl",        "d", "",      lambda t, s: t.mWheels[2].mWear),
    ("tire_wear_rr",        "d", "",      lambda t, s: t.mWheels[3].mWear),

    # tire load
    ("tire_load_fl",        "d", "N",     lambda t, s: t.mWheels[0].mTireLoad),
    ("tire_load_fr",        "d", "N",     lambda t, s: t.mWheels[1].mTireLoad),
    ("tire_load_rl",        "d", "N",     lambda t, s: t.mWheels[2].mTireLoad),
    ("tire_load_rr",        "d", "N",     lambda t, s: t.mWheels[3].mTireLoad),

    # grip fraction
    ("grip_fract_fl",       "d", "",      lambda t, s: t.mWheels[0].mGripFract),
    ("grip_fract_fr",       "d", "",      lambda t, s: t.mWheels[1].mGripFract),
    ("grip_fract_rl",       "d", "",      lambda t, s: t.mWheels[2].mGripFract),
    ("grip_fract_rr",       "d", "",      lambda t, s: t.mWheels[3].mGripFract),

    # lateral / longitudinal forces
    ("lat_force_fl",        "d", "N",     lambda t, s: t.mWheels[0].mLateralForce),
    ("lat_force_fr",        "d", "N",     lambda t, s: t.mWheels[1].mLateralForce),
    ("lat_force_rl",        "d", "N",     lambda t, s: t.mWheels[2].mLateralForce),
    ("lat_force_rr",        "d", "N",     lambda t, s: t.mWheels[3].mLateralForce),
    ("long_force_fl",       "d", "N",     lambda t, s: t.mWheels[0].mLongitudinalForce),
    ("long_force_fr",       "d", "N",     lambda t, s: t.mWheels[1].mLongitudinalForce),
    ("long_force_rl",       "d", "N",     lambda t, s: t.mWheels[2].mLongitudinalForce),
    ("long_force_rr",       "d", "N",     lambda t, s: t.mWheels[3].mLongitudinalForce),

    # wheel rotation (radians/sec → degrees/sec)
    ("wheel_rot_fl",        "d", "°/s",   lambda t, s: _rad_to_deg(t.mWheels[0].mRotation)),
    ("wheel_rot_fr",        "d", "°/s",   lambda t, s: _rad_to_deg(t.mWheels[1].mRotation)),
    ("wheel_rot_rl",        "d", "°/s",   lambda t, s: _rad_to_deg(t.mWheels[2].mRotation)),
    ("wheel_rot_rr",        "d", "°/s",   lambda t, s: _rad_to_deg(t.mWheels[3].mRotation)),

    # camber (radians → degrees)
    ("camber_fl",           "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[0].mCamber)),
    ("camber_fr",           "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[1].mCamber)),
    ("camber_rl",           "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[2].mCamber)),
    ("camber_rr",           "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[3].mCamber)),

    # toe (radians → degrees)
    ("toe_fl",              "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[0].mToe)),
    ("toe_fr",              "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[1].mToe)),
    ("toe_rl",              "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[2].mToe)),
    ("toe_rr",              "d", "°",     lambda t, s: _rad_to_deg(t.mWheels[3].mToe)),

    # flat / detached per wheel
    ("tire_flat_fl",        "?", "",      lambda t, s: bool(t.mWheels[0].mFlat)),
    ("tire_flat_fr",        "?", "",      lambda t, s: bool(t.mWheels[1].mFlat)),
    ("tire_flat_rl",        "?", "",      lambda t, s: bool(t.mWheels[2].mFlat)),
    ("tire_flat_rr",        "?", "",      lambda t, s: bool(t.mWheels[3].mFlat)),
    ("wheel_detached_fl",   "?", "",      lambda t, s: bool(t.mWheels[0].mDetached)),
    ("wheel_detached_fr",   "?", "",      lambda t, s: bool(t.mWheels[1].mDetached)),
    ("wheel_detached_rl",   "?", "",      lambda t, s: bool(t.mWheels[2].mDetached)),
    ("wheel_detached_rr",   "?", "",      lambda t, s: bool(t.mWheels[3].mDetached)),

    # ---- scoring channels ----
    ("total_laps",          "i", "",      lambda t, s: s.mTotalLaps),
    ("lap_dist",            "d", "m",     lambda t, s: s.mLapDist),
    ("best_lap_time",       "d", "s",     lambda t, s: s.mBestLapTime),
    ("last_lap_time",       "d", "s",     lambda t, s: s.mLastLapTime),
    ("best_sector1",        "d", "s",     lambda t, s: s.mBestSector1),
    ("best_sector2",        "d", "s",     lambda t, s: s.mBestSector2),
    ("last_sector1",        "d", "s",     lambda t, s: s.mLastSector1),
    ("last_sector2",        "d", "s",     lambda t, s: s.mLastSector2),
    ("cur_sector1",         "d", "s",     lambda t, s: s.mCurSector1),
    ("cur_sector2",         "d", "s",     lambda t, s: s.mCurSector2),
    ("num_pitstops",        "i", "",      lambda t, s: s.mNumPitstops),
    ("num_penalties",       "i", "",      lambda t, s: s.mNumPenalties),
    ("place",               "B", "",      lambda t, s: s.mPlace),
    ("time_behind_next",    "d", "s",     lambda t, s: s.mTimeBehindNext),
    ("time_behind_leader",  "d", "s",     lambda t, s: s.mTimeBehindLeader),
    ("in_pits",             "?", "",      lambda t, s: bool(s.mInPits)),
    ("pit_state",           "B", "",      lambda t, s: s.mPitState),
    ("drs_state",           "?", "",      lambda t, s: bool(s.mDRSState)),
    ("flag",                "B", "",      lambda t, s: s.mFlag),
    ("time_into_lap",       "d", "s",     lambda t, s: s.mTimeIntoLap),
    ("estimated_lap_time",  "d", "s",     lambda t, s: s.mEstimatedLapTime),
]


def _build_channel_map() -> dict[str, ChannelDescriptor]:
    """Build the lookup table of all available channels."""
    return {
        name: ChannelDescriptor(name=name, type_code=tc, unit=unit, extractor=ext)
        for name, tc, unit, ext in _CHANNEL_DEFS
    }


#: Immutable map ``channel_name → ChannelDescriptor`` for every available channel.
ALL_CHANNELS: dict[str, ChannelDescriptor] = _build_channel_map()


# ---------------------------------------------------------------------------
# Header encoding helpers
# ---------------------------------------------------------------------------

# struct format character → byte size
_TYPE_SIZES: dict[str, int] = {"d": 8, "f": 4, "i": 4, "B": 1, "?": 1}


def _channel_table_bytes(channels: list[ChannelDescriptor]) -> bytes:
    """Encode the channel definition table as length-prefixed binary.

    Layout (per channel, all little-endian):
        1 byte  — name length *n*
        *n* bytes — name (UTF-8)
        1 byte  — type code (ASCII)
        1 byte  — unit length *u*
        *u* bytes — unit (UTF-8)
    """
    parts: list[bytes] = []
    for ch in channels:
        name_b = ch.name.encode("utf-8")
        unit_b = ch.unit.encode("utf-8")
        parts.append(struct.pack("<B", len(name_b)))
        parts.append(name_b)
        parts.append(struct.pack("<c", ch.type_code.encode("ascii")))
        parts.append(struct.pack("<B", len(unit_b)))
        parts.append(unit_b)
    return b"".join(parts)


# ---------------------------------------------------------------------------
# TMUSerializer
# ---------------------------------------------------------------------------

class TMUSerializer:
    """Configurable binary serializer for LMU telemetry frames.

    Parameters
    ----------
    channels : list[str] | None
        Channel names to record.  ``None`` (default) records **all** channels.
        Names are matched case-insensitively against the catalogue.

    Raises
    ------
    ValueError
        If any requested channel name is not in the catalogue.
    """

    __slots__ = ("_channels", "_frame_struct")

    def __init__(self, channels: list[str] | None = None) -> None:
        if channels is None:
            self._channels: list[ChannelDescriptor] = list(ALL_CHANNELS.values())
        else:
            selected: list[ChannelDescriptor] = []
            for name in channels:
                key = name.lower()
                # Allow case-insensitive lookup
                desc = ALL_CHANNELS.get(key)
                if desc is None:
                    # Try original casing
                    desc = ALL_CHANNELS.get(name)
                if desc is None:
                    raise ValueError(
                        f"Unknown channel {name!r}. "
                        f"Available: {sorted(ALL_CHANNELS)}"
                    )
                selected.append(desc)
            self._channels = selected

        # Pre-compile a single ``struct.Struct`` for frame packing.
        # Frame = timestamp (double) + one value per channel.
        fmt = "<d" + "".join(ch.type_code for ch in self._channels)
        self._frame_struct = struct.Struct(fmt)

    # -- public properties --------------------------------------------------

    @property
    def channels(self) -> list[ChannelDescriptor]:
        """Return the active channel list (read-only copy)."""
        return list(self._channels)

    @property
    def channel_names(self) -> list[str]:
        """Return names of active channels."""
        return [ch.name for ch in self._channels]

    @property
    def frame_size(self) -> int:
        """Size of one binary frame in bytes."""
        return self._frame_struct.size

    # -- encoding -----------------------------------------------------------

    def encode_header(
        self,
        *,
        track: str = "",
        car: str = "",
        driver: str = "",
        sample_rate: float = 60.0,
    ) -> bytes:
        """Encode the file header.

        Layout (little-endian)::

            4 bytes  — magic ``TMU\\x00``
            2 bytes  — format version (uint16)
            2 bytes  — channel count (uint16)
            4 bytes  — metadata JSON length *M* (uint32)
            M bytes  — metadata JSON (UTF-8)
            variable — channel definition table

        The metadata block is a UTF-8 JSON object with session info.
        """
        meta = json.dumps(
            {
                "track": track,
                "car": car,
                "driver": driver,
                "sample_rate": sample_rate,
            },
            separators=(",", ":"),
        ).encode("utf-8")

        channel_table = _channel_table_bytes(self._channels)

        header = bytearray()
        header += MAGIC
        header += struct.pack("<H", FORMAT_VERSION)
        header += struct.pack("<H", len(self._channels))
        header += struct.pack("<I", len(meta))
        header += meta
        header += channel_table
        return bytes(header)

    def encode_frame(self, telemetry, scoring, timestamp: float | None = None) -> bytes:
        """Encode one data frame from live struct instances.

        Parameters
        ----------
        telemetry : LMUVehicleTelemetry
            Player vehicle telemetry struct.
        scoring : LMUVehicleScoring
            Player vehicle scoring struct.
        timestamp : float | None
            Explicit timestamp (seconds).  Defaults to ``telemetry.mElapsedTime``.

        Returns
        -------
        bytes
            Flat binary frame (``self.frame_size`` bytes).
        """
        ts = timestamp if timestamp is not None else telemetry.mElapsedTime
        values = [ts]
        for ch in self._channels:
            values.append(ch.extractor(telemetry, scoring))
        return self._frame_struct.pack(*values)

    # -- decoding (for verification / tooling) ------------------------------

    def decode_frame(self, data: bytes, offset: int = 0) -> dict[str, Any]:
        """Decode a single frame back into a dict.

        Returns
        -------
        dict
            ``{"timestamp": float, "channel_name": value, ...}``
        """
        values = self._frame_struct.unpack_from(data, offset)
        result: dict[str, Any] = {"timestamp": values[0]}
        for i, ch in enumerate(self._channels):
            result[ch.name] = values[i + 1]
        return result

    @staticmethod
    def decode_header(data: bytes) -> tuple[dict[str, Any], list[ChannelDescriptor], int]:
        """Decode a file header from raw bytes.

        Returns
        -------
        tuple[dict, list[ChannelDescriptor], int]
            ``(metadata_dict, channel_descriptors, offset_after_header)``

        Raises
        ------
        ValueError
            If magic bytes or version are invalid.
        """
        offset = 0

        # magic
        magic = data[offset:offset + 4]
        if magic != MAGIC:
            raise ValueError(f"Invalid magic bytes: {magic!r}")
        offset += 4

        # version
        (version,) = struct.unpack_from("<H", data, offset)
        if version != FORMAT_VERSION:
            raise ValueError(f"Unsupported format version: {version}")
        offset += 2

        # channel count
        (num_channels,) = struct.unpack_from("<H", data, offset)
        offset += 2

        # metadata
        (meta_len,) = struct.unpack_from("<I", data, offset)
        offset += 4
        meta_json = data[offset:offset + meta_len].decode("utf-8")
        metadata = json.loads(meta_json)
        offset += meta_len

        # channel table
        channels: list[ChannelDescriptor] = []
        for _ in range(num_channels):
            (name_len,) = struct.unpack_from("<B", data, offset)
            offset += 1
            name = data[offset:offset + name_len].decode("utf-8")
            offset += name_len
            type_code = data[offset:offset + 1].decode("ascii")
            offset += 1
            (unit_len,) = struct.unpack_from("<B", data, offset)
            offset += 1
            unit = data[offset:offset + unit_len].decode("utf-8")
            offset += unit_len
            channels.append(ChannelDescriptor(
                name=name, type_code=type_code, unit=unit,
            ))

        return metadata, channels, offset

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def available_channels() -> list[str]:
        """Return a sorted list of all available channel names."""
        return sorted(ALL_CHANNELS)

    def __repr__(self) -> str:
        return (
            f"TMUSerializer(channels={len(self._channels)}, "
            f"frame_size={self.frame_size})"
        )
