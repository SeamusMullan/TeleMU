# Strategy Tool Specs

!!! warning "Planned Feature"
    These tools are not yet implemented. This document provides specifications for agent implementation.

Each tool is a QObject that receives data from the `DataSourceAdapter`, maintains state, and emits signals when results change.

## FuelTool

Tracks fuel consumption and predicts fuel requirements.

### Inputs

| Channel | Source | Frequency |
|---------|--------|-----------|
| `mFuel` | telemetry | every frame |
| `mFuelCapacity` | telemetry | session start |
| `mTotalLaps` / lap change | scoring | per lap |
| `mMaxLaps` | scoring | session start |

### State

```python
class FuelTool(QObject):
    fuel_updated = Signal()

    fuel_current: float          # current fuel (litres)
    fuel_capacity: float         # tank capacity
    consumption_per_lap: list[float]  # history of per-lap consumption
    consumption_avg: float       # rolling average
    laps_remaining_fuel: float   # fuel / avg consumption
    laps_remaining_race: int     # max_laps - current_lap
    fuel_to_add: float           # fuel needed at next stop to finish
    fuel_saving_target: float    # consumption needed to finish without stopping
```

### Calculations

- **Consumption per lap**: `fuel_at_lap_start[n] - fuel_at_lap_start[n+1]`
- **Rolling average**: last 5 laps (or all if < 5)
- **Laps remaining**: `fuel_current / consumption_avg`
- **Fuel to add**: `(laps_remaining_race × consumption_avg) - fuel_current` (clamp to 0)
- **Fuel saving target**: `fuel_current / laps_remaining_race`

---

## TyreTool

Monitors tyre temperatures, wear, and predicts degradation.

### Inputs

| Channel | Source | Frequency |
|---------|--------|-----------|
| `mWheels[i].mTemperature[0..2]` | telemetry | every frame |
| `mWheels[i].mWear` | telemetry | every frame |
| `mWheels[i].mPressure` | telemetry | every frame |
| `mWheels[i].mBrakeTemp` | telemetry | every frame |
| Lap change | scoring | per lap |

### State

```python
class TyreTool(QObject):
    tyres_updated = Signal()

    temps: list[list[float]]       # [FL, FR, RL, RR] × [left, centre, right]
    wear: list[float]              # [FL, FR, RL, RR] 0.0–1.0
    pressures: list[float]         # [FL, FR, RL, RR] kPa
    brake_temps: list[float]       # [FL, FR, RL, RR] °C
    wear_per_lap: list[list[float]]  # history per tyre
    wear_rate_avg: list[float]     # avg wear rate per tyre per lap
    estimated_life: list[float]    # laps until critical wear per tyre
    temp_trend: list[str]          # "rising", "stable", "falling" per tyre
```

### Calculations

- **Temp conversion**: `mTemperature[i] - 273.15` (Kelvin → Celsius)
- **Temp balance**: compare left/centre/right for camber assessment
- **Wear rate**: `(wear[lap_n] - wear[lap_n+1])` per lap (wear decreases = more worn)
- **Estimated life**: `wear_current / wear_rate_avg`
- **Optimal pit window**: when any tyre's estimated life < 3 laps

---

## GapTool

Tracks gaps to cars ahead and behind, identifies undercut/overcut opportunities.

### Inputs

| Channel | Source | Frequency |
|---------|--------|-----------|
| `mTimeBehindNext` | scoring | every update |
| `mTimeBehindLeader` | scoring | every update |
| `mPlace` | scoring | every update |
| `mLapDist` | scoring | every update |
| `mInPits` (all vehicles) | scoring | every update |

### State

```python
class GapTool(QObject):
    gaps_updated = Signal()

    gap_ahead: float            # seconds to car ahead
    gap_behind: float           # seconds to car behind
    gap_leader: float           # seconds to leader
    position: int               # current position
    gap_trend_ahead: list[float]  # history of gap_ahead per lap
    gap_trend_behind: list[float]
    cars_in_pits: list[int]     # positions of cars currently in pits
```

### Calculations

- **Gap trend**: is the gap opening or closing? Linear regression over last 5 data points
- **Undercut window**: if car ahead pits and gap < pit_time_loss, flag opportunity
- **DRS range**: gap_ahead < 1.0s → "DRS available"

---

## StintTool

Manages stint tracking and pace analysis.

### Inputs

| Channel | Source | Frequency |
|---------|--------|-----------|
| `mLastLapTime` | scoring | per lap |
| `mTotalLaps` | scoring | per lap |
| `mInPits` | scoring | every update |
| `mFuel` | telemetry | per lap |
| Tyre wear | TyreTool | per lap |

### State

```python
class StintTool(QObject):
    stint_updated = Signal()

    current_stint: int              # stint number (increments on pit exit)
    stint_lap_count: int            # laps in current stint
    stint_laps: list[float]         # lap times in current stint
    stint_avg_pace: float           # average lap time in stint
    stint_best: float               # best lap in stint
    pace_degradation: float         # seconds per lap pace loss (linear fit)
    stint_history: list[dict]       # [{stint_num, laps, avg_pace, tyre_compound, fuel_start}, ...]
```

### Calculations

- **Stint detection**: new stint starts when `mInPits` transitions from True to False
- **Pace degradation**: linear regression of lap times over stint — positive slope = losing pace
- **Stint comparison**: compare current stint avg pace to previous stints at same lap count

---

## SectorTool

Sector-by-sector performance analysis.

### Inputs

| Channel | Source | Frequency |
|---------|--------|-----------|
| `mCurSector1` | scoring | per sector |
| `mCurSector2` | scoring | per sector |
| `mLastSector1` | scoring | per lap |
| `mLastSector2` | scoring | per lap |
| `mLastLapTime` | scoring | per lap |
| `mBestSector1` | scoring | per lap |
| `mBestSector2` | scoring | per lap |
| `mBestLapTime` | scoring | per lap |

### State

```python
class SectorTool(QObject):
    sectors_updated = Signal()

    sector_times: list[list[float]]  # [S1, S2, S3] per lap
    sector_bests: list[float]        # best time per sector
    sector_deltas: list[float]       # current vs best per sector
    weakest_sector: int              # sector with biggest avg delta to best
    theoretical_best: float          # sum of best sectors
```

### Calculations

- **Sector 3**: `mLastLapTime - mLastSector2` (S2 is cumulative S1+S2)
- **Sector delta**: `current_sector - best_sector`
- **Weakest sector**: sector with highest average delta across all laps
- **Theoretical best**: `best_S1 + (best_S2 - best_S1) + best_S3`

!!! note "Sector numbering"
    LMU's `mSector` field uses unusual numbering: 0=sector3, 1=sector1, 2=sector2. The SectorTool should normalise this to 1-indexed (S1, S2, S3).

---

## PitTool

Pit stop strategy calculations.

### Inputs

| Channel | Source | Frequency |
|---------|--------|-----------|
| `mInPits` | scoring | every update |
| `mPitState` | scoring | every update |
| `mLapDist` + `mPitLapDist` | scoring | session start |
| Fuel data | FuelTool | per lap |
| Tyre data | TyreTool | per lap |
| Gap data | GapTool | per lap |

### State

```python
class PitTool(QObject):
    pit_updated = Signal()

    pit_time_loss: float          # estimated time lost per pit stop (seconds)
    pit_history: list[dict]       # [{lap, duration, fuel_added, tyres_changed}, ...]
    optimal_pit_lap: int          # recommended lap to pit
    strategy_options: list[dict]  # [{stops, pit_laps, total_time_estimate}, ...]
```

### Calculations

- **Pit time loss**: measured from pit entry to pit exit, minus normal lap time for that segment
- **Optimal pit lap**: minimise total race time considering fuel load, tyre deg, pit time loss
- **Strategy comparison**: 1-stop vs 2-stop vs 3-stop total time estimates

### Strategy Comparison Table

The PitTool generates a comparison of strategies:

| Strategy | Pit Laps | Fuel per Stint | Est. Total Time |
|----------|----------|---------------|-----------------|
| 1-stop | [12] | 60L, 55L | 1:42:30 |
| 2-stop | [8, 16] | 42L, 42L, 40L | 1:42:15 |
| 3-stop | [6, 12, 18] | 32L each | 1:42:45 |

## Agent Notes

- **Files to create**: one file per tool in `LMUPI/lmupi/strategy/` — `fuel.py`, `tyres.py`, `gaps.py`, `stint.py`, `sector.py`, `pit.py`
- **Base class**: consider a `StrategyTool(QObject)` base with common `on_telemetry_update` / `on_scoring_update` methods
- **Pattern**: each tool is stateful — it accumulates data over the session; reset on session change
- **Units**: all times in seconds, fuel in litres, temperatures in Celsius, pressures in kPa
- **Sector numbering**: normalise LMU's 0=S3, 1=S1, 2=S2 to 1=S1, 2=S2, 3=S3 immediately on ingestion
- **Testing**: unit test each tool with a sequence of mock updates; verify predictions match hand calculations
- **Related issues**: check project tracker for individual tool issues
