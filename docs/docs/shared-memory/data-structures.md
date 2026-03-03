# Shared Memory Data Structures

Complete field reference for LMU's shared memory interface, as mapped in `lmu_data.py`. All structs use `_pack_ = 4` to match the C++ layout.

## Struct Hierarchy

```
LMUObjectOut
├── generic: LMUGeneric
│   ├── events: LMUEvent (16 event flags)
│   ├── gameVersion: int
│   ├── FFBTorque: float
│   └── appInfo: LMUApplicationState
├── paths: LMUPathData (5 × MAX_PATH_LENGTH strings)
├── scoring: LMUScoringData
│   ├── scoringInfo: LMUScoringInfo (session/track/weather)
│   └── vehScoringInfo: LMUVehicleScoring[104] (per-vehicle lap/position)
└── telemetry: LMUTelemetryData
    ├── activeVehicles: uint8
    ├── playerVehicleIdx: uint8
    ├── playerHasVehicle: bool
    └── telemInfo: LMUVehicleTelemetry[104] (per-vehicle telemetry)
        └── mWheels: LMUWheel[4] (per-wheel data)
```

## LMUVehicleTelemetry — Key Fields

The primary struct for live telemetry. One per vehicle, indexed by vehicle slot.

### Identity & Timing

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mID` | int | — | Slot ID (can be reused in multiplayer) |
| `mDeltaTime` | double | seconds | Time since last update |
| `mElapsedTime` | double | seconds | Game session time |
| `mLapNumber` | int | — | Current lap number |
| `mLapStartET` | double | seconds | Time this lap started |
| `mVehicleName` | char[64] | — | Vehicle name |
| `mTrackName` | char[64] | — | Track name |

### Position & Motion

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mPos` | LMUVect3 | meters | World position |
| `mLocalVel` | LMUVect3 | m/s | Velocity in vehicle-local coords |
| `mLocalAccel` | LMUVect3 | m/s² | Acceleration in vehicle-local coords |
| `mOri` | LMUVect3[3] | — | Orientation matrix rows |
| `mLocalRot` | LMUVect3 | rad/s | Rotational velocity |
| `mLocalRotAccel` | LMUVect3 | rad/s² | Rotational acceleration |

!!! tip "Computing speed in km/h"
    ```python
    import math
    vel = data.telemetry.telemInfo[idx].mLocalVel
    speed_ms = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
    speed_kmh = speed_ms * 3.6
    ```

### Driver Inputs

| Field | Type | Range | Notes |
|-------|------|-------|-------|
| `mGear` | int | -1..n | -1=reverse, 0=neutral, 1+=forward |
| `mEngineRPM` | double | RPM | Current engine RPM |
| `mEngineMaxRPM` | double | RPM | Rev limit |
| `mUnfilteredThrottle` | double | 0.0–1.0 | Raw throttle input |
| `mUnfilteredBrake` | double | 0.0–1.0 | Raw brake input |
| `mUnfilteredSteering` | double | -1.0–1.0 | Raw steering (left to right) |
| `mUnfilteredClutch` | double | 0.0–1.0 | Raw clutch input |
| `mFilteredThrottle` | double | 0.0–1.0 | After TC processing |
| `mFilteredBrake` | double | 0.0–1.0 | After ABS processing |
| `mFilteredSteering` | double | -1.0–1.0 | After assists |
| `mFilteredClutch` | double | 0.0–1.0 | After assists |

!!! tip "Detecting TC/ABS activation"
    ```python
    tc_active = (mUnfilteredThrottle - mFilteredThrottle) > 0.05
    abs_active = (mUnfilteredBrake - mFilteredBrake) > 0.05
    ```

### Fuel & Engine

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mFuel` | double | litres | Current fuel level |
| `mFuelCapacity` | double | litres | Tank capacity |
| `mEngineWaterTemp` | double | °C | Water temperature |
| `mEngineOilTemp` | double | °C | Oil temperature |
| `mEngineTorque` | double | N·m | Current engine torque |
| `mOverheating` | bool | — | Overheating icon shown |
| `mTurboBoostPressure` | double | — | Turbo boost if available |

### EV / Hybrid

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mBatteryChargeFraction` | double | 0.0–1.0 | Battery charge |
| `mElectricBoostMotorTorque` | double | N·m | Negative = regen |
| `mElectricBoostMotorRPM` | double | RPM | Boost motor speed |
| `mElectricBoostMotorTemperature` | double | °C | Motor temp |
| `mElectricBoostWaterTemperature` | double | °C | Motor cooler temp |
| `mElectricBoostMotorState` | uint8 | 0–3 | 0=unavail, 1=inactive, 2=propulsion, 3=regen |

### Aero & Ride

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mFrontWingHeight` | double | meters | Front wing height |
| `mFrontRideHeight` | double | meters | Front ride height |
| `mRearRideHeight` | double | meters | Rear ride height |
| `mDrag` | double | — | Drag coefficient |
| `mFrontDownforce` | double | — | Front downforce |
| `mRearDownforce` | double | — | Rear downforce |
| `mFront3rdDeflection` | double | — | Front 3rd spring deflection |
| `mRear3rdDeflection` | double | — | Rear 3rd spring deflection |

### Tyres & Compounds

| Field | Type | Notes |
|-------|------|-------|
| `mFrontTireCompoundIndex` | uint8 | Index within brand |
| `mRearTireCompoundIndex` | uint8 | Index within brand |
| `mFrontTireCompoundName` | char[18] | Compound name |
| `mRearTireCompoundName` | char[18] | Compound name |

### Status Flags

| Field | Type | Notes |
|-------|------|-------|
| `mScheduledStops` | uint8 | Planned pitstops |
| `mDetached` | bool | Parts detached (besides wheels) |
| `mHeadlights` | bool | Headlights on |
| `mSpeedLimiter` | uint8 | Pit limiter active |
| `mCurrentSector` | int | Zero-based; pitlane in sign bit |
| `mMaxGears` | uint8 | Maximum forward gears |
| `mDeltaBest` | double | Delta to best lap |

## LMUWheel — Per-Wheel Data

Four wheels: `mWheels[0]`=FL, `[1]`=FR, `[2]`=RL, `[3]`=RR.

### Temperature & Pressure

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mTemperature[3]` | double[3] | Kelvin | Left / Centre / Right (subtract 273.15 for °C) |
| `mTireCarcassTemperature` | double | Kelvin | Average carcass temp |
| `mTireInnerLayerTemperature[3]` | double[3] | Kelvin | Inner rubber layer |
| `mPressure` | double | kPa | Tyre pressure |
| `mBrakeTemp` | double | °C | Brake disc temperature |

### Wear & Grip

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mWear` | double | 0.0–1.0 | Fraction of max wear (not linear with grip) |
| `mGripFract` | double | — | Fraction of contact patch sliding |
| `mFlat` | bool | — | Tyre is flat |
| `mDetached` | bool | — | Wheel detached |

### Suspension & Forces

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mSuspensionDeflection` | double | meters | Suspension travel |
| `mRideHeight` | double | meters | Ride height at wheel |
| `mSuspForce` | double | Newtons | Pushrod load |
| `mLateralForce` | double | Newtons | Lateral tyre force |
| `mLongitudinalForce` | double | Newtons | Longitudinal tyre force |
| `mTireLoad` | double | Newtons | Vertical tyre load |
| `mBrakePressure` | double | 0.0–1.0 | Brake pressure (will become kPa in future) |
| `mRotation` | double | rad/s | Wheel rotational speed |
| `mCamber` | double | radians | Camber angle |
| `mToe` | double | radians | Current toe angle |

### Surface

| Field | Type | Notes |
|-------|------|-------|
| `mTerrainName` | char[16] | Material prefix from TDF |
| `mSurfaceType` | uint8 | 0=dry, 1=wet, 2=grass, 3=dirt, 4=gravel, 5=rumblestrip, 6=special |

## LMUVehicleScoring — Per-Vehicle Scoring

### Lap Times

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mBestLapTime` | double | seconds | Best lap |
| `mLastLapTime` | double | seconds | Last completed lap |
| `mBestSector1` | double | seconds | Best S1 |
| `mBestSector2` | double | seconds | Best S1+S2 cumulative |
| `mLastSector1` | double | seconds | Last S1 |
| `mLastSector2` | double | seconds | Last S1+S2 cumulative |
| `mCurSector1` | double | seconds | Current S1 if valid |
| `mCurSector2` | double | seconds | Current S1+S2 if valid |
| `mTotalLaps` | short | — | Laps completed |

### Position & Gaps

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mPlace` | uint8 | — | 1-based position |
| `mTimeBehindNext` | double | seconds | Gap to car ahead |
| `mLapsBehindNext` | int | — | Laps behind car ahead |
| `mTimeBehindLeader` | double | seconds | Gap to leader |
| `mLapsBehindLeader` | int | — | Laps behind leader |
| `mLapDist` | double | meters | Distance around track |

### Status

| Field | Type | Notes |
|-------|------|-------|
| `mInPits` | bool | Between pit entrance and exit |
| `mPitState` | uint8 | 0=none, 1=request, 2=entering, 3=stopped, 4=exiting |
| `mFlag` | uint8 | 0=green, 6=blue |
| `mDRSState` | bool | DRS active |
| `mIsPlayer` | bool | Is this the player's vehicle |
| `mControl` | int8 | -1=nobody, 0=local, 1=AI, 2=remote, 3=replay |
| `mFinishStatus` | int8 | 0=none, 1=finished, 2=DNF, 3=DQ |
| `mFuelFraction` | uint8 | 0x00=0%, 0xFF=100% fuel/battery remaining |

## LMUScoringInfo — Session Data

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mTrackName` | char[64] | — | Track name |
| `mSession` | int | — | 0=test, 1-4=practice, 5-8=qual, 9=warmup, 10-13=race |
| `mCurrentET` | double | seconds | Current session time |
| `mEndET` | double | seconds | Session end time |
| `mMaxLaps` | int | — | Maximum laps |
| `mLapDist` | double | meters | Track length |
| `mNumVehicles` | int | — | Current vehicle count |
| `mGamePhase` | uint8 | — | 0=before, 3=formation, 5=green, 6=SC, 8=over |

### Weather

| Field | Type | Unit | Notes |
|-------|------|------|-------|
| `mAmbientTemp` | double | °C | Air temperature |
| `mTrackTemp` | double | °C | Track temperature |
| `mDarkCloud` | double | 0.0–1.0 | Cloud darkness |
| `mRaining` | double | 0.0–1.0 | Rain severity |
| `mWind` | LMUVect3 | m/s | Wind vector |
| `mMinPathWetness` | double | 0.0–1.0 | Min track wetness |
| `mMaxPathWetness` | double | 0.0–1.0 | Max track wetness |
| `mAvgPathWetness` | double | 0.0–1.0 | Average track wetness |

## LMUEvent — Update Flags

Used by `MMapControl` to gate buffer copies:

| Flag | Purpose |
|------|---------|
| `SME_UPDATE_SCORING` | Scoring data has been updated |
| `SME_UPDATE_TELEMETRY` | Telemetry data has been updated |
| `SME_ENTER_REALTIME` | Entered real-time (on track) |
| `SME_EXIT_REALTIME` | Exited real-time (back to monitor) |
| `SME_START_SESSION` | Session started |
| `SME_END_SESSION` | Session ended |

## Constants

| Constant | Value | Notes |
|----------|-------|-------|
| `LMU_SHARED_MEMORY_FILE` | `"LMU_Data"` | mmap name |
| `MAX_MAPPED_VEHICLES` | `104` | Array size for all vehicle data |
| `MAX_PATH_LENGTH` | `260` | Windows MAX_PATH |

## Agent Notes

- **Source file**: `LMUPI/lmupi/sharedmem/lmu_data.py`
- All structs use `_pack_ = 4` — must match the C++ `#pragma pack(4)`
- Temperature fields in Kelvin need `- 273.15` for Celsius
- `mSector` in scoring uses unusual numbering: 0=sector3, 1=sector1, 2=sector2
- `mCurrentSector` in telemetry stores pitlane in the sign bit (`0x80000000`)
- When LMU updates its header, compare `SharedMemoryInterface.hpp` field-by-field against `lmu_data.py`
- `lmu_type.py` mirrors these structs as abstract type-annotation classes for IDE support
