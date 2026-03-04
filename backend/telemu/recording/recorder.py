"""Async telemetry recorder — subscribes to TelemetryReader and writes .tmu files.

File layout
-----------
[8 bytes : magic ``b"TMUV2REC"``]
[4 bytes : header JSON length, uint32 little-endian]
[N bytes : UTF-8 JSON header (track, vehicle, driver, channels, sample_rate_hz …)]
[StreamCompressor output — LZ4 chunks, chunk-index table, magic b"TMU\\x01"]

Each binary frame inside the StreamCompressor is::

    float64 timestamp | float64 ch_0 | float64 ch_1 | …

Signals (register via ``on_*`` methods)
----------------------------------------
* ``recording_started(path: Path)``
* ``recording_stopped(path: Path, stats: RecordingStats)``
* ``error(exc: Exception)``
* ``stats_updated(stats: RecordingStats)``

Usage::

    recorder = TelemetryRecorder(output_dir="recordings", sample_rate=30)
    recorder.on_recording_started(lambda p: print(f"Recording: {p}"))
    recorder.on_recording_stopped(lambda p, s: print(f"Saved {s.frames_written} frames"))
    await recorder.start(reader, track_name="Spa", vehicle_name="GR010")
    ...
    await recorder.stop()
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import struct
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from telemu.recording.compressor import StreamCompressor

logger = logging.getLogger(__name__)

# File magic identifying the recorder format
RECORDER_MAGIC = b"TMUV2REC"
_HEADER_LEN_FMT = "<I"  # uint32 little-endian

# Valid sample rates (Hz)
VALID_SAMPLE_RATES: frozenset[int] = frozenset({10, 20, 30, 60})

# How often (seconds) to emit a stats_updated signal during recording
_STATS_INTERVAL_S = 1.0


@dataclass
class RecordingStats:
    """Snapshot of recorder statistics."""

    frames_written: int = 0
    bytes_written: int = 0
    duration_s: float = 0.0
    drop_count: int = 0


class TelemetryRecorder:
    """Async recorder that subscribes to a TelemetryReader/DemoReader and writes
    LZ4-compressed binary ``.tmu`` files.

    Parameters
    ----------
    output_dir:
        Directory where ``.tmu`` files are written.  Created if absent.
    sample_rate:
        Recording rate in Hz.  Must be one of ``{10, 20, 30, 60}``.
    ring_buffer_size:
        Maximum number of frames buffered between the reader callback and the
        disk-writer task.  Frames are silently dropped when the buffer is full.
    channels:
        Ordered list of channel names to record.  ``None`` records every
        channel present in the first frame received.
    chunk_frames:
        Number of frames per compressed LZ4 chunk.  Defaults to
        ``sample_rate`` (one chunk per second).
    """

    def __init__(
        self,
        output_dir: Path | str = "recordings",
        sample_rate: int = 60,
        ring_buffer_size: int = 1200,
        channels: list[str] | None = None,
        chunk_frames: int | None = None,
    ) -> None:
        if sample_rate not in VALID_SAMPLE_RATES:
            raise ValueError(
                f"sample_rate must be one of {sorted(VALID_SAMPLE_RATES)}, got {sample_rate}"
            )

        self._output_dir = Path(output_dir)
        self._sample_rate = sample_rate
        self._ring_buffer_size = ring_buffer_size
        self._channels = channels
        self._chunk_frames = chunk_frames if chunk_frames is not None else sample_rate

        # Runtime state
        self._recording = False
        self._paused = False
        self._reader: Any = None
        self._queue: asyncio.Queue | None = None
        self._writer_task: asyncio.Task | None = None
        self._current_file: Path | None = None
        self._stats = RecordingStats()
        self._start_mono: float = 0.0

        # Signal callbacks
        self._on_started: list[Callable[[Path], Any]] = []
        self._on_stopped: list[Callable[[Path | None, RecordingStats], Any]] = []
        self._on_error: list[Callable[[Exception], Any]] = []
        self._on_stats: list[Callable[[RecordingStats], Any]] = []

    # ── Signal registration ───────────────────────────────────────────────────

    def on_recording_started(self, callback: Callable[[Path], Any]) -> None:
        """Register a callback invoked when recording begins."""
        self._on_started.append(callback)

    def on_recording_stopped(
        self, callback: Callable[[Path | None, RecordingStats], Any]
    ) -> None:
        """Register a callback invoked when recording ends."""
        self._on_stopped.append(callback)

    def on_error(self, callback: Callable[[Exception], Any]) -> None:
        """Register a callback invoked on writer errors."""
        self._on_error.append(callback)

    def on_stats_updated(self, callback: Callable[[RecordingStats], Any]) -> None:
        """Register a callback invoked periodically with live statistics."""
        self._on_stats.append(callback)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        """``True`` while recording (including when paused)."""
        return self._recording

    @property
    def is_paused(self) -> bool:
        """``True`` while recording is paused."""
        return self._paused

    @property
    def current_file(self) -> Path | None:
        """Path to the file being written, or ``None`` if not recording."""
        return self._current_file

    @property
    def stats(self) -> RecordingStats:
        """Live copy of recording statistics."""
        duration = (
            time.monotonic() - self._start_mono if self._recording else self._stats.duration_s
        )
        return RecordingStats(
            frames_written=self._stats.frames_written,
            bytes_written=self._stats.bytes_written,
            duration_s=duration,
            drop_count=self._stats.drop_count,
        )

    # ── Control API ───────────────────────────────────────────────────────────

    async def start(
        self,
        reader: Any,
        *,
        track_name: str = "",
        vehicle_name: str = "",
        driver_name: str = "",
    ) -> None:
        """Start recording.

        Parameters
        ----------
        reader:
            A ``TelemetryReader`` or ``DemoReader`` instance with
            ``subscribe()`` / ``unsubscribe()`` methods.
        track_name, vehicle_name, driver_name:
            Optional metadata embedded in the file header.
        """
        if self._recording:
            return

        self._output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_track = track_name.replace(" ", "_").replace("/", "-")[:32] if track_name else "unknown"
        self._current_file = self._output_dir / f"{ts}_{safe_track}.tmu"

        self._queue = asyncio.Queue(maxsize=self._ring_buffer_size)
        self._stats = RecordingStats()
        self._start_mono = time.monotonic()
        self._recording = True
        self._paused = False

        self._reader = reader
        reader.subscribe(self._on_frame)

        self._writer_task = asyncio.create_task(
            self._writer_loop(
                self._current_file,
                track_name=track_name,
                vehicle_name=vehicle_name,
                driver_name=driver_name,
            )
        )

        self._fire(self._on_started, self._current_file)

    async def stop(self) -> Path | None:
        """Stop recording, flush and finalize the file.

        Returns the path to the completed ``.tmu`` file, or ``None`` if no
        recording was active.
        """
        if not self._recording:
            return None

        self._recording = False
        self._paused = False

        if self._reader is not None:
            try:
                self._reader.unsubscribe(self._on_frame)
            except (ValueError, Exception):
                pass
            self._reader = None

        # Send sentinel so the writer task can exit cleanly
        if self._queue is not None:
            try:
                await self._queue.put(None)
            except Exception:
                pass

        if self._writer_task is not None:
            try:
                await self._writer_task
            except Exception:
                pass
            self._writer_task = None

        self._stats.duration_s = time.monotonic() - self._start_mono
        completed = self._current_file
        self._fire(self._on_stopped, completed, self._stats)
        return completed

    def pause(self) -> None:
        """Pause frame capture (frames from the reader are ignored)."""
        self._paused = True

    def resume(self) -> None:
        """Resume frame capture after a pause."""
        self._paused = False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_frame(self, frame: Any) -> None:
        """Synchronous callback from TelemetryReader; enqueues onto the ring buffer."""
        if not self._recording or self._paused or self._queue is None:
            return
        try:
            self._queue.put_nowait(frame)
        except asyncio.QueueFull:
            self._stats.drop_count += 1

    async def _writer_loop(
        self,
        path: Path,
        *,
        track_name: str,
        vehicle_name: str,
        driver_name: str,
    ) -> None:
        """Async writer task: dequeues frames and writes LZ4-compressed binary."""
        interval = 1.0 / self._sample_rate  # minimum seconds between recorded frames
        last_ts: float = -1.0
        last_stats_mono = time.monotonic()

        buf = io.BytesIO()
        compressor: StreamCompressor | None = None
        channel_names: list[str] = []
        fmt = ""

        try:
            # Block until the first frame arrives (or stop sentinel)
            first_frame = await self._queue.get()
            if first_frame is None:
                return  # stopped before receiving any frames

            channel_names = (
                list(self._channels)
                if self._channels is not None
                else sorted(first_frame.channels.keys())
            )
            num_channels = len(channel_names)
            fmt = "<d" + "d" * num_channels  # timestamp + float64 per channel

            compressor = StreamCompressor(buf, chunk_frames=self._chunk_frames, algorithm="lz4")

            raw = _pack_frame(fmt, channel_names, first_frame)
            compressor.write_frame(raw)
            self._stats.frames_written += 1
            last_ts = first_frame.ts

            while True:
                try:
                    frame = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    # No frames for a while; emit stats and keep waiting
                    now = time.monotonic()
                    if now - last_stats_mono >= _STATS_INTERVAL_S:
                        self._emit_stats()
                        last_stats_mono = now
                    continue

                if frame is None:  # sentinel — stop requested
                    break

                # Sample rate control: skip frames closer than interval
                if frame.ts - last_ts < interval * 0.9:
                    continue

                raw = _pack_frame(fmt, channel_names, frame)
                compressor.write_frame(raw)
                self._stats.frames_written += 1
                last_ts = frame.ts

                now = time.monotonic()
                if now - last_stats_mono >= _STATS_INTERVAL_S:
                    self._emit_stats()
                    last_stats_mono = now

            compressor.finalize()

            # Build the file header JSON
            header = {
                "track": track_name,
                "vehicle": vehicle_name,
                "driver": driver_name,
                "sample_rate_hz": self._sample_rate,
                "channels": channel_names,
                "frame_fmt": fmt,
                "frame_size": struct.calcsize(fmt),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")

            # Write: magic | header_len | header | compressed_data
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(RECORDER_MAGIC)
                fh.write(struct.pack(_HEADER_LEN_FMT, len(header_bytes)))
                fh.write(header_bytes)
                fh.write(buf.getvalue())

            self._stats.bytes_written = path.stat().st_size

        except Exception as exc:
            logger.exception("TelemetryRecorder writer error: %s", exc)
            self._fire(self._on_error, exc)
        finally:
            if compressor is not None and not compressor._finalized:
                try:
                    compressor.finalize()
                except Exception:
                    pass

    def _emit_stats(self) -> None:
        stats = self.stats
        for cb in self._on_stats:
            try:
                cb(stats)
            except Exception:
                logger.exception("Error in stats_updated callback")

    def _fire(self, callbacks: list, *args: Any) -> None:
        for cb in callbacks:
            try:
                cb(*args)
            except Exception:
                logger.exception("Error in recorder signal callback")


# ── File reading helpers ──────────────────────────────────────────────────────


def read_recorder_file(path: Path | str) -> tuple[dict, list[dict]]:
    """Read a recorder ``.tmu`` file.

    Returns ``(header_dict, frames)`` where each frame is a dict with
    ``"timestamp"`` plus one key per channel.

    Raises
    ------
    ValueError
        If *path* does not start with the recorder magic bytes.
    """
    from telemu.recording.compressor import decompress_chunk, read_index

    path = Path(path)
    with open(path, "rb") as fh:
        magic = fh.read(len(RECORDER_MAGIC))
        if magic != RECORDER_MAGIC:
            raise ValueError(f"Not a recorder .tmu file (bad magic: {magic!r})")
        (hdr_len,) = struct.unpack(_HEADER_LEN_FMT, fh.read(4))
        header = json.loads(fh.read(hdr_len).decode("utf-8"))
        compressed_start = fh.tell()
        compressed_data = fh.read()

    channel_names: list[str] = header["channels"]
    fmt: str = header["frame_fmt"]
    frame_size: int = header["frame_size"]

    compressed_buf = io.BytesIO(compressed_data)
    index = read_index(compressed_buf)

    frames: list[dict] = []
    for chunk_meta in index["chunks"]:
        raw_chunk = decompress_chunk(compressed_buf, chunk_meta, algorithm="lz4")
        offset = 0
        while offset + frame_size <= len(raw_chunk):
            values = struct.unpack(fmt, raw_chunk[offset : offset + frame_size])
            frame: dict = {"timestamp": values[0]}
            for i, name in enumerate(channel_names):
                frame[name] = values[i + 1]
            frames.append(frame)
            offset += frame_size

    return header, frames


# ── Module-private helpers ────────────────────────────────────────────────────


def _pack_frame(fmt: str, channel_names: list[str], frame: Any) -> bytes:
    """Pack a TelemetryFrame into a flat binary frame."""
    values: list[float] = [frame.ts]
    channels = frame.channels
    for name in channel_names:
        values.append(channels.get(name, 0.0))
    return struct.pack(fmt, *values)
