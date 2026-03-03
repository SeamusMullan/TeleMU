"""Shared memory telemetry reader for Le Mans Ultimate.

Reads from LMU's shared memory via pyLMUSharedMemory and pushes data
into a LiveDashboard instance. Runs in a background QThread to avoid
blocking the UI.

Usage:
    reader = TelemetryReader(dashboard)
    reader.start()   # begins polling shared memory
    reader.stop()    # stops polling
"""

from __future__ import annotations

import ctypes
import logging
import math

from PySide6.QtCore import QThread, Signal

from lmupi.compressed_recorder import CompressedRecorder
from lmupi.sharedmem.lmu_data import LMUConstants, LMUObjectOut
from lmupi.sharedmem.lmu_mmap import MMapControl

logger = logging.getLogger(__name__)

# Kelvin → Celsius
_K2C = 273.15


def _speed_from_local_vel(vel) -> float:
    """Compute speed in km/h from local velocity vector (m/s)."""
    return math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2) * 3.6


def _format_laptime(seconds: float) -> str:
    """Format a lap time in seconds to m:ss.mmm."""
    if seconds <= 0:
        return "--:--.---"
    mins = int(seconds) // 60
    secs = seconds - mins * 60
    return f"{mins}:{secs:06.3f}"


class TelemetryReader(QThread):
    """Background thread that polls LMU shared memory and pushes to dashboard.

    Signals:
        connected: emitted when shared memory is successfully opened
        disconnected: emitted when shared memory is closed or game exits
        error: emitted with error message string
    """

    connected = Signal()
    disconnected = Signal()
    error = Signal(str)

    def __init__(self, dashboard, poll_ms: int = 16, parent=None) -> None:
        """
        Args:
            dashboard: LiveDashboard instance to push data into.
            poll_ms: polling interval in milliseconds (~60Hz default).
        """
        super().__init__(parent)
        self._dashboard = dashboard
        self._poll_ms = poll_ms
        self._running = False
        self._mmap: MMapControl | None = None

        # Track lap changes for lap info updates
        self._last_lap = -1

        # Optional compressed recording
        self._recorder: CompressedRecorder | None = None

    def start_reading(self) -> None:
        """Start the reader thread."""
        self._running = True
        self.start()

    def stop_reading(self) -> None:
        """Signal the reader to stop and wait for it to finish."""
        self._running = False
        self.wait(2000)

    # ── recording ──────────────────────────────────────────────────────

    def start_recording(self, path: str, *, compressor: str = "lz4", chunk_frames: int = 64) -> None:
        """Begin recording telemetry frames to a compressed file.

        Args:
            path: destination file path.
            compressor: ``"lz4"`` (default) or ``"zstd"``.
            chunk_frames: frames per compressed chunk.
        """
        rec = CompressedRecorder(path, compressor=compressor, chunk_frames=chunk_frames)
        rec.start()
        self._recorder = rec
        logger.info("Recording started → %s", path)

    def stop_recording(self) -> None:
        """Finalize and close the current recording."""
        rec = self._recorder
        if rec is not None:
            rec.finalize()
            self._recorder = None
            logger.info("Recording stopped")

    def run(self) -> None:
        """Thread main loop."""
        try:
            self._mmap = MMapControl(
                LMUConstants.LMU_SHARED_MEMORY_FILE,
                LMUObjectOut,
            )
            self._mmap.create(access_mode=0)  # copy access for thread safety
        except Exception as exc:
            self.error.emit(f"Could not open shared memory: {exc}")
            return

        self.connected.emit()
        logger.info("TelemetryReader: connected to LMU shared memory")

        try:
            while self._running:
                self._poll_once()
                self.msleep(self._poll_ms)
        except Exception as exc:
            self.error.emit(f"Telemetry read error: {exc}")
        finally:
            self.stop_recording()
            try:
                self._mmap.close()
            except Exception:
                pass
            self._mmap = None
            self.disconnected.emit()
            logger.info("TelemetryReader: disconnected")

    def _poll_once(self) -> None:
        """Read one frame from shared memory and push to dashboard."""
        mmap = self._mmap
        if mmap is None or mmap.data is None:
            return

        mmap.update()
        data = mmap.data

        # Record raw telemetry snapshot if recording is active
        if self._recorder is not None:
            frame_bytes = bytes(ctypes.string_at(
                ctypes.addressof(data), ctypes.sizeof(data)
            ))
            self._recorder.write_frame(frame_bytes)

        # Check if game is running
        version = data.generic.gameVersion
        if not version:
            return

        tele = data.telemetry
        scor = data.scoring

        if not tele.playerHasVehicle:
            return

        idx = tele.playerVehicleIdx
        if idx < 0 or idx >= LMUConstants.MAX_MAPPED_VEHICLES:
            return

        vt = tele.telemInfo[idx]  # player vehicle telemetry
        vs = scor.vehScoringInfo[idx]  # player vehicle scoring

        dash = self._dashboard

        # -- Core telemetry --
        speed = _speed_from_local_vel(vt.mLocalVel)
        dash.push("Speed", speed)
        dash.push("RPM", vt.mEngineRPM)
        dash.push("Throttle", vt.mUnfilteredThrottle * 100.0)
        dash.push("Brake", vt.mUnfilteredBrake * 100.0)
        dash.push("Gear", float(vt.mGear))
        dash.push("Steering", vt.mUnfilteredSteering * vt.mPhysicalSteeringWheelRange)

        # Update max RPM on gauge if available
        if vt.mEngineMaxRPM > 0:
            rpm_ch = dash._channels.get("RPM")
            if rpm_ch and rpm_ch.max_val != vt.mEngineMaxRPM:
                rpm_ch.max_val = vt.mEngineMaxRPM
                rpm_ch.warn_high = vt.mEngineMaxRPM * 0.95

        # -- Tyre temps (center temperature, Kelvin → Celsius) --
        wheel_names = ["Tyre FL", "Tyre FR", "Tyre RL", "Tyre RR"]
        for i, name in enumerate(wheel_names):
            temp_k = vt.mWheels[i].mTemperature[1]  # center temp
            dash.push(name, temp_k - _K2C)

        # -- Fuel --
        dash.push("Fuel", vt.mFuel)

        # Update fuel capacity on channel if available
        if vt.mFuelCapacity > 0:
            fuel_ch = dash._channels.get("Fuel")
            if fuel_ch and fuel_ch.max_val != vt.mFuelCapacity:
                fuel_ch.max_val = vt.mFuelCapacity

        # -- Brake temp (average across 4 wheels) --
        brake_temps = [vt.mWheels[i].mBrakeTemp for i in range(4)]
        avg_brake_temp = sum(brake_temps) / 4.0
        dash.push("Brake Temp", avg_brake_temp)

        # -- Status indicators --
        dash._status_row.set_active("DRS", bool(vs.mDRSState), "#27ae60")
        dash._status_row.set_active("PIT", bool(vs.mInPits), "#f5a623")

        # Flag: 6 = blue flag
        flag_active = vs.mFlag != 0
        flag_color = "#4fc3f7" if vs.mFlag == 6 else "#f5a623"
        dash._status_row.set_active("FLAG", flag_active, flag_color)

        # TC / ABS — inferred from telemetry deltas
        # Throttle cut (TC active) when filtered < unfiltered significantly
        tc_active = (vt.mUnfilteredThrottle - vt.mFilteredThrottle) > 0.05
        dash._status_row.set_active("TC", tc_active, "#f5a623")

        # ABS active when filtered brake < unfiltered brake significantly
        abs_active = (vt.mUnfilteredBrake - vt.mFilteredBrake) > 0.05
        dash._status_row.set_active("ABS", abs_active, "#f5a623")

        # -- Lap info --
        current_lap = vs.mTotalLaps + 1
        if current_lap != self._last_lap or self._last_lap == -1:
            self._last_lap = current_lap

            last_time = _format_laptime(vs.mLastLapTime)
            best_time = _format_laptime(vs.mBestLapTime)

            sectors = [
                _format_laptime(vs.mLastSector1),
                _format_laptime(vs.mLastSector2 - vs.mLastSector1 if vs.mLastSector2 > vs.mLastSector1 else vs.mLastSector2),
                _format_laptime(vs.mLastLapTime - vs.mLastSector2 if vs.mLastLapTime > vs.mLastSector2 else 0),
            ]

            dash._lap_panel.update_lap(current_lap, last_time, best_time, sectors)
