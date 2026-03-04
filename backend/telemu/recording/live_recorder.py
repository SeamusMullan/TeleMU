"""Live telemetry recorder — captures TelemetryFrame events to a .tmu file.

The recorder subscribes to the telemetry reader, buffers incoming frames
in memory, and flushes them to a zstd-compressed NDJSON .tmu file on stop.

File naming follows the ``track_car_YYYY-MM-DD_HHMMSS.tmu`` pattern using
whatever metadata is available at start time.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

import zstandard as zstd

if TYPE_CHECKING:
    from telemu.reader import TelemetryFrame

logger = logging.getLogger(__name__)

_MAGIC = b"TMU\x01"
_HEADER_LEN_FMT = "<I"


def _make_filename(track: str, car: str) -> str:
    """Generate an auto filename following track_car_YYYY-MM-DD_HHMMSS pattern."""
    import datetime

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H%M%S")

    def _slug(s: str) -> str:
        """Lowercase, replace spaces/special chars with underscores."""
        import re
        s = re.sub(r"[^\w\s-]", "", s.lower())
        return re.sub(r"[\s-]+", "_", s).strip("_") or "unknown"

    return f"{_slug(track)}_{_slug(car)}_{date_str}.tmu"


class LiveRecorder:
    """Records live telemetry frames to a .tmu NDJSON file.

    Usage::

        recorder = LiveRecorder()
        # wired up in app lifespan:
        reader.subscribe(recorder.on_frame)
        # later:
        await recorder.start(output_dir=Path("/path/to/dir"))
        await recorder.stop()
    """

    def __init__(self) -> None:
        self._active = False
        self._frames: list[bytes] = []
        self._start_time: float = 0.0
        self._output_path: Path | None = None
        self._track: str = ""
        self._car: str = ""
        # Rate tracking: (timestamp, cumulative_bytes) pairs
        self._rate_window: deque[tuple[float, int]] = deque(maxlen=60)
        self._bytes_written: int = 0
        self._lock = asyncio.Lock()

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def active(self) -> bool:
        return self._active

    async def start(
        self,
        *,
        output_dir: Path,
        filename: str | None = None,
        track: str = "",
        car: str = "",
    ) -> None:
        """Begin recording.  Raises ``RuntimeError`` if already active."""
        async with self._lock:
            if self._active:
                raise RuntimeError("Recording already active")
            output_dir.mkdir(parents=True, exist_ok=True)
            fname = filename or _make_filename(track or "unknown", car or "unknown")
            self._output_path = output_dir / fname
            self._track = track
            self._car = car
            self._frames = []
            self._bytes_written = 0
            self._rate_window.clear()
            self._start_time = time.monotonic()
            self._active = True
            logger.info("LiveRecorder: started → %s", self._output_path)

    async def stop(self) -> dict:
        """Stop recording, flush file, and return status dict."""
        async with self._lock:
            if not self._active:
                raise RuntimeError("No active recording")
            self._active = False
            path = self._output_path
            frames = self._frames
            track = self._track
            car = self._car
            duration = time.monotonic() - self._start_time

        # Write outside the lock to avoid blocking incoming frames
        assert path is not None
        await asyncio.to_thread(_write_tmu, path, track, car, frames)
        size = path.stat().st_size if path.exists() else 0
        logger.info(
            "LiveRecorder: saved %d frames (%.1f s) → %s",
            len(frames),
            duration,
            path,
        )
        return {
            "active": False,
            "filename": path.name,
            "output_path": str(path),
            "duration_seconds": duration,
            "file_size_bytes": size,
            "data_rate_bps": 0.0,
        }

    def on_frame(self, frame: TelemetryFrame) -> None:
        """Callback — must be thread-safe (called from asyncio task)."""
        if not self._active:
            return
        obj: dict = {"ts": frame.ts, "channels": frame.channels}
        if frame.lap_info:
            obj["lap_marker"] = frame.lap_info
        line = json.dumps(obj, separators=(",", ":")).encode()
        self._frames.append(line)
        self._bytes_written += len(line)
        now = time.monotonic()
        self._rate_window.append((now, self._bytes_written))

    def status(self) -> dict:
        """Return current recording status as a plain dict."""
        if not self._active:
            return {
                "active": False,
                "filename": "",
                "output_path": "",
                "duration_seconds": 0.0,
                "file_size_bytes": 0,
                "data_rate_bps": 0.0,
            }
        duration = time.monotonic() - self._start_time
        # Approx in-memory size (pre-flush)
        in_mem_bytes = self._bytes_written
        # Data rate over last ~5 seconds
        rate = _compute_rate(self._rate_window)
        return {
            "active": True,
            "filename": self._output_path.name if self._output_path else "",
            "output_path": str(self._output_path) if self._output_path else "",
            "duration_seconds": duration,
            "file_size_bytes": in_mem_bytes,
            "data_rate_bps": rate,
        }

    def update_metadata(self, *, track: str = "", car: str = "") -> None:
        """Update track/car info (called once real data arrives)."""
        if self._active and self._track == "" and track:
            self._track = track
        if self._active and self._car == "" and car:
            self._car = car


# ── Helpers ─────────────────────────────────────────────────────────────────


def _compute_rate(window: deque[tuple[float, int]]) -> float:
    """Bytes per second over the oldest sample in the window."""
    if len(window) < 2:
        return 0.0
    oldest_ts, oldest_bytes = window[0]
    newest_ts, newest_bytes = window[-1]
    dt = newest_ts - oldest_ts
    if dt <= 0:
        return 0.0
    return (newest_bytes - oldest_bytes) / dt


def _write_tmu(path: Path, track: str, car: str, frames: list[bytes]) -> None:
    """Write buffered frames to disk using the NDJSON .tmu format."""
    import datetime

    header = {
        "track": track,
        "car": car,
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "channels": [],
    }
    hdr_bytes = json.dumps(header, separators=(",", ":")).encode()
    payload = b"\n".join(frames)
    cctx = zstd.ZstdCompressor(level=3)
    compressed = cctx.compress(payload)

    with open(path, "wb") as fh:
        fh.write(_MAGIC)
        fh.write(struct.pack(_HEADER_LEN_FMT, len(hdr_bytes)))
        fh.write(hdr_bytes)
        fh.write(compressed)
