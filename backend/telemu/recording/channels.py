"""Channel definitions for .tmu binary frame serialisation.

Each channel maps a field (or computed value) from LMUVehicleTelemetry /
LMUVehicleScoring to a named, typed slot in a flat binary frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

# ── Conversion constants ──────────────────────────────────────────────

_K2C = 273.15  # Kelvin → Celsius offset
_RAD2DEG = 180.0 / math.pi  # radians → degrees factor
_MS2KMH = 3.6  # m/s → km/h factor


# ── Channel definition ────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ChannelDef:
    """A single telemetry/scoring channel.

    Attributes:
        name:    Unique channel identifier.
        fmt:     ``struct`` format character (e.g. ``'d'`` for float64).
        unit:    Human-readable unit string.
        source:  ``'telemetry'``, ``'scoring'``, or ``'computed'``.
        extract: Callable ``(telemetry, scoring) -> value``.
    """

    name: str
    fmt: str
    unit: str
    source: str
    extract: Callable[[Any, Any], int | float | bool]


# ── Helpers ───────────────────────────────────────────────────────────

_WHEEL_NAMES = ("fl", "fr", "rl", "rr")


def _speed(t: Any, _s: Any) -> float:
    """Compute speed in km/h from local velocity vector."""
    v = t.mLocalVel
    return math.sqrt(v.x**2 + v.y**2 + v.z**2) * _MS2KMH


def _ch(
    name: str, fmt: str, unit: str, source: str,
    extract: Callable[[Any, Any], int | float | bool],
) -> ChannelDef:
    """Shorthand constructor."""
    return ChannelDef(name=name, fmt=fmt, unit=unit, source=source, extract=extract)


def _build_wheel_channels() -> dict[str, ChannelDef]:
    """Generate per-wheel channel definitions for all four wheels."""
    chs: dict[str, ChannelDef] = {}
    for i, wn in enumerate(_WHEEL_NAMES):
        p = f"wheel_{wn}"

        # Surface temperatures (K → °C)
        chs[f"{p}_temp_l"] = _ch(
            f"{p}_temp_l", "d", "°C", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mTemperature[0] - _K2C,
        )
        chs[f"{p}_temp"] = _ch(
            f"{p}_temp", "d", "°C", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mTemperature[1] - _K2C,
        )
        chs[f"{p}_temp_r"] = _ch(
            f"{p}_temp_r", "d", "°C", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mTemperature[2] - _K2C,
        )
        # Carcass temperature (K → °C)
        chs[f"{p}_carcass_temp"] = _ch(
            f"{p}_carcass_temp", "d", "°C", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mTireCarcassTemperature - _K2C,
        )
        # Pressure
        chs[f"{p}_pressure"] = _ch(
            f"{p}_pressure", "d", "kPa", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mPressure,
        )
        # Wear
        chs[f"{p}_wear"] = _ch(
            f"{p}_wear", "d", "", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mWear,
        )
        # Brake temperature
        chs[f"{p}_brake_temp"] = _ch(
            f"{p}_brake_temp", "d", "°C", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mBrakeTemp,
        )
        # Brake pressure
        chs[f"{p}_brake_pressure"] = _ch(
            f"{p}_brake_pressure", "d", "", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mBrakePressure,
        )
        # Suspension deflection
        chs[f"{p}_susp_deflection"] = _ch(
            f"{p}_susp_deflection", "d", "m", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mSuspensionDeflection,
        )
        # Ride height
        chs[f"{p}_ride_height"] = _ch(
            f"{p}_ride_height", "d", "m", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mRideHeight,
        )
        # Suspension force
        chs[f"{p}_susp_force"] = _ch(
            f"{p}_susp_force", "d", "N", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mSuspForce,
        )
        # Lateral force
        chs[f"{p}_lateral_force"] = _ch(
            f"{p}_lateral_force", "d", "N", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mLateralForce,
        )
        # Longitudinal force
        chs[f"{p}_long_force"] = _ch(
            f"{p}_long_force", "d", "N", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mLongitudinalForce,
        )
        # Tire load
        chs[f"{p}_tire_load"] = _ch(
            f"{p}_tire_load", "d", "N", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mTireLoad,
        )
        # Grip fraction
        chs[f"{p}_grip"] = _ch(
            f"{p}_grip", "d", "", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mGripFract,
        )
        # Camber (rad → °)
        chs[f"{p}_camber"] = _ch(
            f"{p}_camber", "d", "°", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mCamber * _RAD2DEG,
        )
        # Toe (rad → °)
        chs[f"{p}_toe"] = _ch(
            f"{p}_toe", "d", "°", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mToe * _RAD2DEG,
        )
        # Wheel rotation speed
        chs[f"{p}_rotation"] = _ch(
            f"{p}_rotation", "d", "rad/s", "telemetry",
            lambda t, s, _i=i: t.mWheels[_i].mRotation,
        )
    return chs


# ── All available channels ────────────────────────────────────────────

ALL_CHANNELS: dict[str, ChannelDef] = {}

# --- Timing / Identity ------------------------------------------------

ALL_CHANNELS["elapsed_time"] = _ch(
    "elapsed_time", "d", "s", "telemetry", lambda t, s: t.mElapsedTime)
ALL_CHANNELS["delta_time"] = _ch(
    "delta_time", "d", "s", "telemetry", lambda t, s: t.mDeltaTime)
ALL_CHANNELS["lap_number"] = _ch(
    "lap_number", "i", "", "telemetry", lambda t, s: t.mLapNumber)
ALL_CHANNELS["lap_start_et"] = _ch(
    "lap_start_et", "d", "s", "telemetry", lambda t, s: t.mLapStartET)

# --- Position ---------------------------------------------------------

ALL_CHANNELS["pos_x"] = _ch(
    "pos_x", "d", "m", "telemetry", lambda t, s: t.mPos.x)
ALL_CHANNELS["pos_y"] = _ch(
    "pos_y", "d", "m", "telemetry", lambda t, s: t.mPos.y)
ALL_CHANNELS["pos_z"] = _ch(
    "pos_z", "d", "m", "telemetry", lambda t, s: t.mPos.z)

# --- Velocity ---------------------------------------------------------

ALL_CHANNELS["speed"] = _ch("speed", "d", "km/h", "computed", _speed)
ALL_CHANNELS["vel_x"] = _ch(
    "vel_x", "d", "m/s", "telemetry", lambda t, s: t.mLocalVel.x)
ALL_CHANNELS["vel_y"] = _ch(
    "vel_y", "d", "m/s", "telemetry", lambda t, s: t.mLocalVel.y)
ALL_CHANNELS["vel_z"] = _ch(
    "vel_z", "d", "m/s", "telemetry", lambda t, s: t.mLocalVel.z)

# --- Acceleration -----------------------------------------------------

ALL_CHANNELS["accel_x"] = _ch(
    "accel_x", "d", "m/s²", "telemetry", lambda t, s: t.mLocalAccel.x)
ALL_CHANNELS["accel_y"] = _ch(
    "accel_y", "d", "m/s²", "telemetry", lambda t, s: t.mLocalAccel.y)
ALL_CHANNELS["accel_z"] = _ch(
    "accel_z", "d", "m/s²", "telemetry", lambda t, s: t.mLocalAccel.z)

# --- Rotation (rad/s → °/s) ------------------------------------------

ALL_CHANNELS["local_rot_x"] = _ch(
    "local_rot_x", "d", "°/s", "telemetry",
    lambda t, s: t.mLocalRot.x * _RAD2DEG)
ALL_CHANNELS["local_rot_y"] = _ch(
    "local_rot_y", "d", "°/s", "telemetry",
    lambda t, s: t.mLocalRot.y * _RAD2DEG)
ALL_CHANNELS["local_rot_z"] = _ch(
    "local_rot_z", "d", "°/s", "telemetry",
    lambda t, s: t.mLocalRot.z * _RAD2DEG)
ALL_CHANNELS["local_rot_accel_x"] = _ch(
    "local_rot_accel_x", "d", "°/s²", "telemetry",
    lambda t, s: t.mLocalRotAccel.x * _RAD2DEG)
ALL_CHANNELS["local_rot_accel_y"] = _ch(
    "local_rot_accel_y", "d", "°/s²", "telemetry",
    lambda t, s: t.mLocalRotAccel.y * _RAD2DEG)
ALL_CHANNELS["local_rot_accel_z"] = _ch(
    "local_rot_accel_z", "d", "°/s²", "telemetry",
    lambda t, s: t.mLocalRotAccel.z * _RAD2DEG)

# --- Driver Inputs ----------------------------------------------------

ALL_CHANNELS["gear"] = _ch(
    "gear", "i", "", "telemetry", lambda t, s: t.mGear)
ALL_CHANNELS["rpm"] = _ch(
    "rpm", "d", "RPM", "telemetry", lambda t, s: t.mEngineRPM)
ALL_CHANNELS["rpm_max"] = _ch(
    "rpm_max", "d", "RPM", "telemetry", lambda t, s: t.mEngineMaxRPM)
ALL_CHANNELS["throttle"] = _ch(
    "throttle", "d", "%", "telemetry", lambda t, s: t.mUnfilteredThrottle * 100.0)
ALL_CHANNELS["brake"] = _ch(
    "brake", "d", "%", "telemetry", lambda t, s: t.mUnfilteredBrake * 100.0)
ALL_CHANNELS["steering"] = _ch(
    "steering", "d", "", "telemetry", lambda t, s: t.mUnfilteredSteering)
ALL_CHANNELS["clutch"] = _ch(
    "clutch", "d", "%", "telemetry", lambda t, s: t.mUnfilteredClutch * 100.0)
ALL_CHANNELS["filtered_throttle"] = _ch(
    "filtered_throttle", "d", "%", "telemetry",
    lambda t, s: t.mFilteredThrottle * 100.0)
ALL_CHANNELS["filtered_brake"] = _ch(
    "filtered_brake", "d", "%", "telemetry",
    lambda t, s: t.mFilteredBrake * 100.0)
ALL_CHANNELS["filtered_steering"] = _ch(
    "filtered_steering", "d", "", "telemetry", lambda t, s: t.mFilteredSteering)
ALL_CHANNELS["filtered_clutch"] = _ch(
    "filtered_clutch", "d", "%", "telemetry",
    lambda t, s: t.mFilteredClutch * 100.0)
ALL_CHANNELS["steering_torque"] = _ch(
    "steering_torque", "d", "N·m", "telemetry",
    lambda t, s: t.mSteeringShaftTorque)

# --- Engine / Fuel ----------------------------------------------------

ALL_CHANNELS["fuel"] = _ch(
    "fuel", "d", "L", "telemetry", lambda t, s: t.mFuel)
ALL_CHANNELS["fuel_capacity"] = _ch(
    "fuel_capacity", "d", "L", "telemetry", lambda t, s: t.mFuelCapacity)
ALL_CHANNELS["water_temp"] = _ch(
    "water_temp", "d", "°C", "telemetry", lambda t, s: t.mEngineWaterTemp)
ALL_CHANNELS["oil_temp"] = _ch(
    "oil_temp", "d", "°C", "telemetry", lambda t, s: t.mEngineOilTemp)
ALL_CHANNELS["engine_torque"] = _ch(
    "engine_torque", "d", "N·m", "telemetry", lambda t, s: t.mEngineTorque)
ALL_CHANNELS["clutch_rpm"] = _ch(
    "clutch_rpm", "d", "RPM", "telemetry", lambda t, s: t.mClutchRPM)
ALL_CHANNELS["turbo_boost"] = _ch(
    "turbo_boost", "d", "", "telemetry", lambda t, s: t.mTurboBoostPressure)

# --- Aero / Ride ------------------------------------------------------

ALL_CHANNELS["front_wing_height"] = _ch(
    "front_wing_height", "d", "m", "telemetry", lambda t, s: t.mFrontWingHeight)
ALL_CHANNELS["front_ride_height"] = _ch(
    "front_ride_height", "d", "m", "telemetry", lambda t, s: t.mFrontRideHeight)
ALL_CHANNELS["rear_ride_height"] = _ch(
    "rear_ride_height", "d", "m", "telemetry", lambda t, s: t.mRearRideHeight)
ALL_CHANNELS["drag"] = _ch(
    "drag", "d", "", "telemetry", lambda t, s: t.mDrag)
ALL_CHANNELS["front_downforce"] = _ch(
    "front_downforce", "d", "", "telemetry", lambda t, s: t.mFrontDownforce)
ALL_CHANNELS["rear_downforce"] = _ch(
    "rear_downforce", "d", "", "telemetry", lambda t, s: t.mRearDownforce)
ALL_CHANNELS["front_3rd_deflection"] = _ch(
    "front_3rd_deflection", "d", "", "telemetry", lambda t, s: t.mFront3rdDeflection)
ALL_CHANNELS["rear_3rd_deflection"] = _ch(
    "rear_3rd_deflection", "d", "", "telemetry", lambda t, s: t.mRear3rdDeflection)

# --- Status / Flags ---------------------------------------------------

ALL_CHANNELS["delta_best"] = _ch(
    "delta_best", "d", "s", "telemetry", lambda t, s: t.mDeltaBest)
ALL_CHANNELS["rear_brake_bias"] = _ch(
    "rear_brake_bias", "d", "", "telemetry", lambda t, s: t.mRearBrakeBias)
ALL_CHANNELS["speed_limiter"] = _ch(
    "speed_limiter", "B", "", "telemetry", lambda t, s: t.mSpeedLimiter)
ALL_CHANNELS["current_sector"] = _ch(
    "current_sector", "i", "", "telemetry", lambda t, s: t.mCurrentSector)
ALL_CHANNELS["overheating"] = _ch(
    "overheating", "?", "", "telemetry", lambda t, s: bool(t.mOverheating))
ALL_CHANNELS["headlights"] = _ch(
    "headlights", "?", "", "telemetry", lambda t, s: bool(t.mHeadlights))

# --- EV / Hybrid ------------------------------------------------------

ALL_CHANNELS["battery_charge"] = _ch(
    "battery_charge", "d", "%", "telemetry",
    lambda t, s: t.mBatteryChargeFraction * 100.0)
ALL_CHANNELS["boost_motor_torque"] = _ch(
    "boost_motor_torque", "d", "N·m", "telemetry",
    lambda t, s: t.mElectricBoostMotorTorque)
ALL_CHANNELS["boost_motor_rpm"] = _ch(
    "boost_motor_rpm", "d", "RPM", "telemetry",
    lambda t, s: t.mElectricBoostMotorRPM)
ALL_CHANNELS["boost_motor_temp"] = _ch(
    "boost_motor_temp", "d", "°C", "telemetry",
    lambda t, s: t.mElectricBoostMotorTemperature)
ALL_CHANNELS["boost_water_temp"] = _ch(
    "boost_water_temp", "d", "°C", "telemetry",
    lambda t, s: t.mElectricBoostWaterTemperature)
ALL_CHANNELS["boost_motor_state"] = _ch(
    "boost_motor_state", "B", "", "telemetry",
    lambda t, s: t.mElectricBoostMotorState)

# --- Per-wheel channels (×4) ------------------------------------------

ALL_CHANNELS.update(_build_wheel_channels())

# --- Scoring channels -------------------------------------------------

ALL_CHANNELS["place"] = _ch(
    "place", "B", "", "scoring", lambda t, s: s.mPlace)
ALL_CHANNELS["total_laps"] = _ch(
    "total_laps", "h", "", "scoring", lambda t, s: s.mTotalLaps)
ALL_CHANNELS["lap_dist"] = _ch(
    "lap_dist", "d", "m", "scoring", lambda t, s: s.mLapDist)
ALL_CHANNELS["best_lap_time"] = _ch(
    "best_lap_time", "d", "s", "scoring", lambda t, s: s.mBestLapTime)
ALL_CHANNELS["last_lap_time"] = _ch(
    "last_lap_time", "d", "s", "scoring", lambda t, s: s.mLastLapTime)
ALL_CHANNELS["best_sector1"] = _ch(
    "best_sector1", "d", "s", "scoring", lambda t, s: s.mBestSector1)
ALL_CHANNELS["best_sector2"] = _ch(
    "best_sector2", "d", "s", "scoring", lambda t, s: s.mBestSector2)
ALL_CHANNELS["last_sector1"] = _ch(
    "last_sector1", "d", "s", "scoring", lambda t, s: s.mLastSector1)
ALL_CHANNELS["last_sector2"] = _ch(
    "last_sector2", "d", "s", "scoring", lambda t, s: s.mLastSector2)
ALL_CHANNELS["cur_sector1"] = _ch(
    "cur_sector1", "d", "s", "scoring", lambda t, s: s.mCurSector1)
ALL_CHANNELS["cur_sector2"] = _ch(
    "cur_sector2", "d", "s", "scoring", lambda t, s: s.mCurSector2)
ALL_CHANNELS["time_behind_next"] = _ch(
    "time_behind_next", "d", "s", "scoring", lambda t, s: s.mTimeBehindNext)
ALL_CHANNELS["laps_behind_next"] = _ch(
    "laps_behind_next", "i", "", "scoring", lambda t, s: s.mLapsBehindNext)
ALL_CHANNELS["time_behind_leader"] = _ch(
    "time_behind_leader", "d", "s", "scoring", lambda t, s: s.mTimeBehindLeader)
ALL_CHANNELS["laps_behind_leader"] = _ch(
    "laps_behind_leader", "i", "", "scoring", lambda t, s: s.mLapsBehindLeader)
ALL_CHANNELS["in_pits"] = _ch(
    "in_pits", "?", "", "scoring", lambda t, s: bool(s.mInPits))
ALL_CHANNELS["pit_state"] = _ch(
    "pit_state", "B", "", "scoring", lambda t, s: s.mPitState)
ALL_CHANNELS["drs"] = _ch(
    "drs", "?", "", "scoring", lambda t, s: bool(s.mDRSState))
ALL_CHANNELS["flag"] = _ch(
    "flag", "B", "", "scoring", lambda t, s: s.mFlag)
ALL_CHANNELS["num_pitstops"] = _ch(
    "num_pitstops", "h", "", "scoring", lambda t, s: s.mNumPitstops)
ALL_CHANNELS["num_penalties"] = _ch(
    "num_penalties", "h", "", "scoring", lambda t, s: s.mNumPenalties)
ALL_CHANNELS["finish_status"] = _ch(
    "finish_status", "b", "", "scoring", lambda t, s: s.mFinishStatus)
ALL_CHANNELS["time_into_lap"] = _ch(
    "time_into_lap", "d", "s", "scoring", lambda t, s: s.mTimeIntoLap)
ALL_CHANNELS["estimated_lap_time"] = _ch(
    "estimated_lap_time", "d", "s", "scoring", lambda t, s: s.mEstimatedLapTime)

# ── Default channel selection ─────────────────────────────────────────

DEFAULT_CHANNELS: list[str] = [
    # Core telemetry
    "elapsed_time",
    "speed",
    "rpm",
    "rpm_max",
    "gear",
    "throttle",
    "brake",
    "steering",
    "clutch",
    "fuel",
    "fuel_capacity",
    # Temperatures
    "water_temp",
    "oil_temp",
    # Tyre temps (centre surface)
    "wheel_fl_temp",
    "wheel_fr_temp",
    "wheel_rl_temp",
    "wheel_rr_temp",
    # Brake temps
    "wheel_fl_brake_temp",
    "wheel_fr_brake_temp",
    "wheel_rl_brake_temp",
    "wheel_rr_brake_temp",
    # Scoring essentials
    "place",
    "best_lap_time",
    "last_lap_time",
    "lap_dist",
    "in_pits",
    "drs",
]
