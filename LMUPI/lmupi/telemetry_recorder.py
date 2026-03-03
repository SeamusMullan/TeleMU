"""TelemetryRecorder — QThread-based engine that captures shared memory data
and writes compressed ``.tmu`` files.

Runs alongside :class:`TelemetryReader` and records telemetry data from
LMU's shared memory into the TeleMU binary format with LZ4 compression.

Usage::

    recorder = TelemetryRecorder(sample_rate=60)
    recorder.start_recording("/path/to/output.tmu")
    # ... later ...
    recorder.stop_recording()

Signals:
    recording_started: Emitted when recording begins writing frames.
    recording_stopped: Emitted when the file is finalized and closed.
    error(str): Emitted with an error message on failure.
    stats_updated(dict): Emitted periodically with recording statistics.
"""

from __future__ import annotations

import collections
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal

from lmupi.sharedmem.lmu_data import LMUConstants, LMUObjectOut
from lmupi.sharedmem.lmu_mmap import MMapControl
from lmupi.tmu_compression import StreamingCompressor
from lmupi.tmu_format import (
    CHUNK_INDEX_SIZE,
    ChannelDef,
    SessionMetadata,
    encode_channel_table,
    encode_chunk_index,
    encode_footer,
    encode_header,
)
from lmupi.tmu_serializer import TelemetrySerializer

logger = logging.getLogger(__name__)

# Supported sample rates (Hz) and their poll intervals (ms)
SAMPLE_RATES: dict[int, int] = {
    10: 100,
    20: 50,
    30: 33,
    60: 16,
}

# How many frames to accumulate per LZ4 chunk
_FRAMES_PER_CHUNK = 64

# Stats update interval in frames
_STATS_INTERVAL_FRAMES = 30


class _RingBuffer:
    """Thread-safe fixed-size ring buffer to decouple reading from disk writes.

    Producers (the polling loop) append frame bytes; the consumer (the
    disk-write section) drains all available frames in bulk.
    """

    def __init__(self, capacity: int = 1024) -> None:
        self._buf: collections.deque[bytes] = collections.deque(maxlen=capacity)
        self._mutex = QMutex()
        self._drop_count = 0

    def put(self, data: bytes) -> bool:
        """Append a frame.  Returns ``False`` if the buffer was full and
        the oldest frame was dropped."""
        with QMutexLocker(self._mutex):
            was_full = len(self._buf) == self._buf.maxlen
            self._buf.append(data)
            if was_full:
                self._drop_count += 1
            return not was_full

    def drain(self) -> list[bytes]:
        """Remove and return all buffered frames."""
        with QMutexLocker(self._mutex):
            items = list(self._buf)
            self._buf.clear()
            return items

    @property
    def drop_count(self) -> int:
        with QMutexLocker(self._mutex):
            return self._drop_count

    def __len__(self) -> int:
        with QMutexLocker(self._mutex):
            return len(self._buf)


class TelemetryRecorder(QThread):
    """Background thread that captures shared memory data and writes
    compressed ``.tmu`` files.

    The recorder opens its own shared memory connection (copy-access) so
    it can run independently of :class:`TelemetryReader`.

    Args:
        sample_rate: Recording sample rate in Hz (10, 20, 30, or 60).
        channels: Optional list of channel definitions.  If ``None``,
            the default channel set from :mod:`tmu_serializer` is used.
        ring_capacity: Maximum frames the ring buffer can hold.
        parent: Optional Qt parent.
    """

    recording_started = Signal()
    recording_stopped = Signal()
    error = Signal(str)
    stats_updated = Signal(dict)

    def __init__(
        self,
        sample_rate: int = 60,
        channels: list[ChannelDef] | None = None,
        ring_capacity: int = 1024,
        parent=None,
    ) -> None:
        super().__init__(parent)

        if sample_rate not in SAMPLE_RATES:
            raise ValueError(
                f"Unsupported sample rate {sample_rate}Hz.  "
                f"Choose from {sorted(SAMPLE_RATES)}."
            )

        self._sample_rate = sample_rate
        self._poll_ms = SAMPLE_RATES[sample_rate]
        self._serializer = TelemetrySerializer(channels)
        self._ring = _RingBuffer(ring_capacity)

        # Thread control (guarded by _state_mutex)
        self._state_mutex = QMutex()
        self._running = False
        self._paused = False
        self._output_path: str | None = None

    # ── Public API (thread-safe) ──────────────────────────

    def start_recording(self, output_path: str) -> None:
        """Begin recording to *output_path*.

        The file will be created/truncated.  The thread is started
        automatically if not already running.
        """
        with QMutexLocker(self._state_mutex):
            if self._running:
                return
            self._output_path = output_path
            self._running = True
            self._paused = False
        self.start()

    def stop_recording(self) -> None:
        """Signal the recorder to stop, finalize the file, and exit."""
        with QMutexLocker(self._state_mutex):
            self._running = False
        self.wait(5000)

    def pause_recording(self) -> None:
        """Pause recording — frames are not captured while paused."""
        with QMutexLocker(self._state_mutex):
            self._paused = True

    def resume_recording(self) -> None:
        """Resume a paused recording."""
        with QMutexLocker(self._state_mutex):
            self._paused = False

    @property
    def is_recording(self) -> bool:
        with QMutexLocker(self._state_mutex):
            return self._running

    @property
    def is_paused(self) -> bool:
        with QMutexLocker(self._state_mutex):
            return self._paused

    # ── Thread entry point ────────────────────────────────

    def run(self) -> None:  # noqa: C901  (complexity acceptable for main loop)
        """Thread main loop — poll shared memory, serialize, compress, write."""
        output_path: str | None
        with QMutexLocker(self._state_mutex):
            output_path = self._output_path

        if not output_path:
            self.error.emit("No output path specified")
            return

        # ── Open shared memory ────────────────────────────
        mmap: MMapControl | None = None
        try:
            mmap = MMapControl(
                LMUConstants.LMU_SHARED_MEMORY_FILE,
                LMUObjectOut,
            )
            mmap.create(access_mode=0)
        except Exception as exc:
            self.error.emit(f"Could not open shared memory: {exc}")
            with QMutexLocker(self._state_mutex):
                self._running = False
            return

        # ── Open output file and write header ─────────────
        try:
            fh = open(output_path, "wb")
        except Exception as exc:
            self.error.emit(f"Could not open output file: {exc}")
            mmap.close()
            with QMutexLocker(self._state_mutex):
                self._running = False
            return

        serializer = self._serializer
        compressor = StreamingCompressor(frames_per_chunk=_FRAMES_PER_CHUNK)

        # Build session metadata from shared memory
        metadata = self._build_metadata(mmap)
        meta_bytes = metadata.to_json_bytes()

        channels = serializer.channels
        ch_table_bytes = encode_channel_table(channels)

        # Compute offsets
        from lmupi.tmu_format import HEADER_SIZE
        metadata_offset = HEADER_SIZE
        metadata_size = len(meta_bytes)
        channel_table_offset = metadata_offset + metadata_size
        channel_table_size = len(ch_table_bytes)
        data_start_offset = channel_table_offset + channel_table_size

        header = encode_header(
            num_channels=len(channels),
            sample_rate=self._sample_rate,
            metadata_offset=metadata_offset,
            metadata_size=metadata_size,
            channel_table_offset=channel_table_offset,
            channel_table_size=channel_table_size,
            data_start_offset=data_start_offset,
        )

        try:
            fh.write(header)
            fh.write(meta_bytes)
            fh.write(ch_table_bytes)
        except Exception as exc:
            self.error.emit(f"Error writing file header: {exc}")
            fh.close()
            mmap.close()
            with QMutexLocker(self._state_mutex):
                self._running = False
            return

        self.recording_started.emit()
        logger.info("TelemetryRecorder: started recording to %s", output_path)

        # ── Main recording loop ───────────────────────────
        frame_count = 0
        bytes_written = data_start_offset
        start_time = time.monotonic()
        stats_counter = 0

        try:
            while True:
                with QMutexLocker(self._state_mutex):
                    if not self._running:
                        break
                    paused = self._paused

                if not paused:
                    # Poll shared memory
                    try:
                        mmap.update()
                    except Exception:
                        pass  # skip this frame if update fails

                    data = mmap.data
                    if data is not None:
                        version = data.generic.gameVersion
                        if version:
                            tele = data.telemetry
                            if tele.playerHasVehicle:
                                idx = tele.playerVehicleIdx
                                if 0 <= idx < LMUConstants.MAX_MAPPED_VEHICLES:
                                    vt = tele.telemInfo[idx]
                                    vs = data.scoring.vehScoringInfo[idx]

                                    timestamp = vt.mElapsedTime
                                    frame_bytes = serializer.serialize_frame(
                                        timestamp, vt, vs,
                                    )
                                    self._ring.put(frame_bytes)

                    # Drain ring buffer and write compressed chunks
                    frames = self._ring.drain()
                    for frame in frames:
                        chunk = compressor.add_frame(frame)
                        if chunk is not None:
                            # Update file offset in the latest chunk index
                            idx_entry = compressor.chunk_indices[-1]
                            idx_entry.file_offset = bytes_written
                            fh.write(chunk)
                            bytes_written += len(chunk)
                            frame_count = compressor.total_frames

                    # Emit stats periodically
                    stats_counter += 1
                    if stats_counter >= _STATS_INTERVAL_FRAMES:
                        stats_counter = 0
                        elapsed = time.monotonic() - start_time
                        self.stats_updated.emit({
                            "frames": frame_count,
                            "bytes_written": bytes_written,
                            "elapsed_seconds": elapsed,
                            "drops": self._ring.drop_count,
                            "ring_usage": len(self._ring),
                        })

                self.msleep(self._poll_ms)

        except Exception as exc:
            self.error.emit(f"Recording error: {exc}")

        # ── Finalize file ─────────────────────────────────
        try:
            # Drain remaining frames from ring buffer
            remaining = self._ring.drain()
            for frame in remaining:
                chunk = compressor.add_frame(frame)
                if chunk is not None:
                    idx_entry = compressor.chunk_indices[-1]
                    idx_entry.file_offset = bytes_written
                    fh.write(chunk)
                    bytes_written += len(chunk)

            # Flush any remaining frames in the compressor
            last_chunk = compressor.flush()
            if last_chunk is not None:
                idx_entry = compressor.chunk_indices[-1]
                idx_entry.file_offset = bytes_written
                fh.write(last_chunk)
                bytes_written += len(last_chunk)

            # Write chunk index table
            index_table_offset = bytes_written
            for entry in compressor.chunk_indices:
                fh.write(encode_chunk_index(entry))

            # Write footer
            footer = encode_footer(
                total_frames=compressor.total_frames,
                index_table_offset=index_table_offset,
                index_entry_count=len(compressor.chunk_indices),
            )
            fh.write(footer)
            fh.flush()
            logger.info(
                "TelemetryRecorder: finalized %s — %d frames, %d chunks",
                output_path,
                compressor.total_frames,
                len(compressor.chunk_indices),
            )
        except Exception as exc:
            self.error.emit(f"Error finalizing recording: {exc}")
        finally:
            fh.close()
            try:
                mmap.close()
            except Exception:
                pass
            with QMutexLocker(self._state_mutex):
                self._running = False
            self.recording_stopped.emit()
            logger.info("TelemetryRecorder: stopped")

    # ── Helpers ───────────────────────────────────────────

    def _build_metadata(self, mmap: MMapControl) -> SessionMetadata:
        """Extract session metadata from current shared memory state."""
        meta = SessionMetadata(
            sample_rate=self._sample_rate,
            date=datetime.now(timezone.utc).isoformat(),
        )
        try:
            mmap.update()
            data = mmap.data
            if data is not None and data.generic.gameVersion:
                scor = data.scoring.scoringInfo
                meta.track = scor.mTrackName.decode("utf-8", errors="replace").rstrip("\x00")

                tele = data.telemetry
                if tele.playerHasVehicle:
                    idx = tele.playerVehicleIdx
                    if 0 <= idx < LMUConstants.MAX_MAPPED_VEHICLES:
                        vt = tele.telemInfo[idx]
                        meta.car = vt.mVehicleName.decode("utf-8", errors="replace").rstrip("\x00")

                        vs = data.scoring.vehScoringInfo[idx]
                        meta.driver = vs.mDriverName.decode("utf-8", errors="replace").rstrip("\x00")
        except Exception:
            pass  # metadata is best-effort
        return meta
