"""Async telemetry reader — polls LMU shared memory and broadcasts via event bus.

Port of LMUPI/lmupi/telemetry_reader.py from QThread to asyncio.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

_K2C = 273.15  # Kelvin → Celsius


def _speed_from_local_vel(vel) -> float:
    """Compute speed in km/h from local velocity vector (m/s)."""
    return math.sqrt(vel.x**2 + vel.y**2 + vel.z**2) * 3.6


def _format_laptime(seconds: float) -> str:
    if seconds <= 0:
        return "--:--.---"
    mins = int(seconds) // 60
    secs = seconds - mins * 60
    return f"{mins}:{secs:06.3f}"


@dataclass
class TelemetryFrame:
    """One snapshot of telemetry + scoring data."""

    ts: float  # monotonic timestamp
    channels: dict[str, float] = field(default_factory=dict)
    status: dict[str, Any] = field(default_factory=dict)
    lap_info: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, Any] | None = None


# Type alias for frame listeners
FrameCallback = Callable[[TelemetryFrame], Any]


class TelemetryReader:
    """Async task that reads LMU shared memory at ~60Hz.

    Replaces the QThread-based reader. Subscribers receive TelemetryFrame objects
    via registered callbacks.
    """

    def __init__(self, poll_ms: int = 16) -> None:
        self._poll_ms = poll_ms
        self._running = False
        self._connected = False
        self._mmap = None
        self._task: asyncio.Task | None = None
        self._callbacks: list[FrameCallback] = []
        self._last_lap = -1

    @property
    def connected(self) -> bool:
        return self._connected

    def subscribe(self, callback: FrameCallback) -> None:
        self._callbacks.append(callback)

    def unsubscribe(self, callback: FrameCallback) -> None:
        self._callbacks.remove(callback)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        """Main polling loop."""
        # Import here to avoid import errors on systems without shared memory
        try:
            from telemu.sharedmem.lmu_data import LMUConstants, LMUObjectOut
            from telemu.sharedmem.lmu_mmap import MMapControl

            self._mmap = MMapControl(LMUConstants.LMU_SHARED_MEMORY_FILE, LMUObjectOut)
            self._mmap.create(access_mode=0)
        except Exception as exc:
            logger.warning("Could not open LMU shared memory: %s", exc)
            self._connected = False
            return

        self._connected = True
        logger.info("TelemetryReader: connected to LMU shared memory")

        try:
            while self._running:
                frame = self._poll_once()
                if frame is not None:
                    for cb in self._callbacks:
                        try:
                            cb(frame)
                        except Exception:
                            logger.exception("Error in telemetry callback")
                await asyncio.sleep(self._poll_ms / 1000.0)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Telemetry read error: %s", exc)
        finally:
            try:
                if self._mmap:
                    self._mmap.close()
            except Exception:
                pass
            self._mmap = None
            self._connected = False
            logger.info("TelemetryReader: disconnected")

    def _poll_once(self) -> TelemetryFrame | None:
        """Read one frame from shared memory."""
        mmap = self._mmap
        if mmap is None or mmap.data is None:
            return None

        mmap.update()
        data = mmap.data

        if not data.generic.gameVersion:
            return None

        tele = data.telemetry
        scor = data.scoring

        if not tele.playerHasVehicle:
            return None

        from telemu.sharedmem.lmu_data import LMUConstants

        idx = tele.playerVehicleIdx
        if idx < 0 or idx >= LMUConstants.MAX_MAPPED_VEHICLES:
            return None

        vt = tele.telemInfo[idx]
        vs = scor.vehScoringInfo[idx]

        channels = {
            "speed": _speed_from_local_vel(vt.mLocalVel),
            "rpm": vt.mEngineRPM,
            "throttle": vt.mUnfilteredThrottle * 100.0,
            "brake": vt.mUnfilteredBrake * 100.0,
            "gear": float(vt.mGear),
            "steering": vt.mUnfilteredSteering * vt.mPhysicalSteeringWheelRange,
            "fuel": vt.mFuel,
            "fuel_capacity": vt.mFuelCapacity,
            "rpm_max": vt.mEngineMaxRPM,
        }

        # Tyre temps (center, K→C)
        wheel_names = ["tyre_fl", "tyre_fr", "tyre_rl", "tyre_rr"]
        for i, name in enumerate(wheel_names):
            channels[name] = vt.mWheels[i].mTemperature[1] - _K2C

        # Brake temp (average)
        channels["brake_temp"] = sum(vt.mWheels[i].mBrakeTemp for i in range(4)) / 4.0

        # Status indicators
        tc_active = (vt.mUnfilteredThrottle - vt.mFilteredThrottle) > 0.05
        abs_active = (vt.mUnfilteredBrake - vt.mFilteredBrake) > 0.05

        status = {
            "drs": bool(vs.mDRSState),
            "pit": bool(vs.mInPits),
            "flag": vs.mFlag,
            "tc": tc_active,
            "abs": abs_active,
        }

        # Lap info
        lap_info: dict[str, Any] = {}
        current_lap = vs.mTotalLaps + 1
        if current_lap != self._last_lap or self._last_lap == -1:
            self._last_lap = current_lap
            lap_info = {
                "lap": current_lap,
                "last_time": _format_laptime(vs.mLastLapTime),
                "best_time": _format_laptime(vs.mBestLapTime),
                "sectors": [
                    _format_laptime(vs.mLastSector1),
                    _format_laptime(
                        vs.mLastSector2 - vs.mLastSector1
                        if vs.mLastSector2 > vs.mLastSector1
                        else vs.mLastSector2
                    ),
                    _format_laptime(
                        vs.mLastLapTime - vs.mLastSector2
                        if vs.mLastLapTime > vs.mLastSector2
                        else 0
                    ),
                ],
            }

        return TelemetryFrame(
            ts=time.monotonic(),
            channels=channels,
            status=status,
            lap_info=lap_info if lap_info else {},
        )


class DemoReader:
    """Generates simulated telemetry for development/testing without LMU."""

    def __init__(self, poll_ms: int = 16) -> None:
        self._poll_ms = poll_ms
        self._running = False
        self._connected = False
        self._task: asyncio.Task | None = None
        self._callbacks: list[FrameCallback] = []
        self._t = 0.0

    @property
    def connected(self) -> bool:
        return self._connected

    def subscribe(self, callback: FrameCallback) -> None:
        self._callbacks.append(callback)

    def unsubscribe(self, callback: FrameCallback) -> None:
        self._callbacks.remove(callback)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        self._connected = True
        logger.info("DemoReader: generating simulated telemetry")
        try:
            while self._running:
                frame = self._generate_frame()
                for cb in self._callbacks:
                    try:
                        cb(frame)
                    except Exception:
                        logger.exception("Error in demo callback")
                await asyncio.sleep(self._poll_ms / 1000.0)
        except asyncio.CancelledError:
            pass
        finally:
            self._connected = False

    def _generate_frame(self) -> TelemetryFrame:
        self._t += self._poll_ms / 1000.0
        t = self._t

        # Simulate a car on track
        speed = 180 + 100 * math.sin(t * 0.3)
        rpm = 4000 + 4000 * (0.5 + 0.5 * math.sin(t * 0.5))
        throttle = max(0, min(100, 50 + 50 * math.sin(t * 0.4)))
        brake = max(0, min(100, 30 * max(0, -math.sin(t * 0.4))))
        gear = max(1, min(7, int(3.5 + 3 * math.sin(t * 0.2))))
        steering = 30 * math.sin(t * 0.8)

        channels = {
            "speed": speed,
            "rpm": rpm,
            "throttle": throttle,
            "brake": brake,
            "gear": float(gear),
            "steering": steering,
            "fuel": max(0, 80 - t * 0.05),
            "fuel_capacity": 110.0,
            "rpm_max": 8500.0,
            "tyre_fl": 85 + 10 * math.sin(t * 0.1),
            "tyre_fr": 87 + 10 * math.sin(t * 0.1 + 0.5),
            "tyre_rl": 82 + 8 * math.sin(t * 0.1 + 1.0),
            "tyre_rr": 84 + 8 * math.sin(t * 0.1 + 1.5),
            "brake_temp": 400 + 200 * abs(math.sin(t * 0.3)),
        }

        status = {
            "drs": int(t) % 30 < 5,
            "pit": False,
            "flag": 0,
            "tc": throttle > 90,
            "abs": brake > 80,
        }

        lap = int(t / 90) + 1
        lap_info = {
            "lap": lap,
            "last_time": f"1:{52 + (lap % 3):.3f}",
            "best_time": "1:52.123",
            "sectors": ["0:32.456", "0:38.789", "0:41.234"],
        }

        return TelemetryFrame(
            ts=time.monotonic(),
            channels=channels,
            status=status,
            lap_info=lap_info,
        )
