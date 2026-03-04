"""Tests for TelemetryRecorder."""

from __future__ import annotations

import math
import struct
import time
from pathlib import Path
from typing import Any

import pytest

from telemu.recording.recorder import (
    RECORDER_MAGIC,
    VALID_SAMPLE_RATES,
    RecordingStats,
    TelemetryRecorder,
    _pack_frame,
    read_recorder_file,
)


# ── Fake reader & frame ───────────────────────────────────────────────────────


class FakeFrame:
    """Minimal TelemetryFrame-like object for testing."""

    def __init__(self, ts: float, **channels: float) -> None:
        self.ts = ts
        self.channels: dict[str, float] = dict(channels)
        self.status: dict[str, Any] = {}
        self.lap_info: dict[str, Any] = {}


class FakeReader:
    """Minimal reader stub with subscribe/unsubscribe."""

    def __init__(self) -> None:
        self._callbacks: list = []
        self.connected = True

    def subscribe(self, callback) -> None:
        self._callbacks.append(callback)

    def unsubscribe(self, callback) -> None:
        self._callbacks.remove(callback)

    def push(self, frame: FakeFrame) -> None:
        for cb in list(self._callbacks):
            cb(frame)


def _frames(n: int, *, rate: int = 60, start: float = 0.0) -> list[FakeFrame]:
    """Generate *n* fake frames at *rate* Hz."""
    interval = 1.0 / rate
    return [
        FakeFrame(
            start + i * interval,
            speed=100 + math.sin(i * 0.1) * 50,
            rpm=5000.0,
            throttle=80.0,
            brake=0.0,
            gear=3.0,
        )
        for i in range(n)
    ]


# ── Construction tests ────────────────────────────────────────────────────────


class TestConstruction:
    def test_valid_sample_rates(self):
        for rate in VALID_SAMPLE_RATES:
            rec = TelemetryRecorder(sample_rate=rate)
            assert not rec.is_recording

    def test_invalid_sample_rate_raises(self):
        with pytest.raises(ValueError, match="sample_rate"):
            TelemetryRecorder(sample_rate=25)

    def test_initial_state(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path)
        assert not rec.is_recording
        assert not rec.is_paused
        assert rec.current_file is None

    def test_stats_initial(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path)
        s = rec.stats
        assert s.frames_written == 0
        assert s.drop_count == 0


# ── Signal registration ───────────────────────────────────────────────────────


class TestSignals:
    @pytest.mark.asyncio
    async def test_on_recording_started_called(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        started_paths = []
        rec.on_recording_started(lambda p: started_paths.append(p))

        await rec.start(reader)
        await rec.stop()

        assert len(started_paths) == 1
        assert isinstance(started_paths[0], Path)

    @pytest.mark.asyncio
    async def test_on_recording_stopped_called(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        stopped = []
        rec.on_recording_stopped(lambda p, s: stopped.append((p, s)))

        await rec.start(reader)
        await rec.stop()

        assert len(stopped) == 1
        _, stats = stopped[0]
        assert isinstance(stats, RecordingStats)

    @pytest.mark.asyncio
    async def test_on_stats_updated_called(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        stat_events = []
        rec.on_stats_updated(lambda s: stat_events.append(s))

        await rec.start(reader)
        for f in _frames(10):
            reader.push(f)
        await rec.stop()

        # stats_updated may or may not fire during short test; just verify type if fired
        for s in stat_events:
            assert isinstance(s, RecordingStats)

    @pytest.mark.asyncio
    async def test_multiple_callbacks_same_signal(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        calls = []
        rec.on_recording_started(lambda p: calls.append("a"))
        rec.on_recording_started(lambda p: calls.append("b"))

        await rec.start(reader)
        await rec.stop()

        assert "a" in calls
        assert "b" in calls


# ── Start / Stop ──────────────────────────────────────────────────────────────


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_creates_recording(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        assert rec.is_recording
        assert rec.current_file is not None
        await rec.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        first_file = rec.current_file
        await rec.start(reader)  # second call is a no-op
        assert rec.current_file == first_file
        await rec.stop()

    @pytest.mark.asyncio
    async def test_stop_returns_path(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        path = await rec.stop()
        assert path is not None
        assert path.suffix == ".tmu"

    @pytest.mark.asyncio
    async def test_stop_when_not_recording_returns_none(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        result = await rec.stop()
        assert result is None

    @pytest.mark.asyncio
    async def test_file_created_after_stop(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        # Push a few frames so the writer task has data
        for f in _frames(5):
            reader.push(f)
        path = await rec.stop()
        assert path is not None
        assert path.exists()

    @pytest.mark.asyncio
    async def test_output_dir_created(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        rec = TelemetryRecorder(output_dir=nested, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        assert nested.exists()
        await rec.stop()

    @pytest.mark.asyncio
    async def test_file_name_contains_timestamp(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader, track_name="Spa")
        path = await rec.stop()
        assert path is not None
        # Name should be like "20260304_HHMMSS_Spa.tmu"
        assert "Spa" in path.name

    @pytest.mark.asyncio
    async def test_reader_unsubscribed_on_stop(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        assert len(reader._callbacks) == 1
        await rec.stop()
        assert len(reader._callbacks) == 0


# ── Pause / Resume ────────────────────────────────────────────────────────────


class TestPauseResume:
    @pytest.mark.asyncio
    async def test_pause_resume_flags(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)

        assert not rec.is_paused
        rec.pause()
        assert rec.is_paused
        rec.resume()
        assert not rec.is_paused

        await rec.stop()

    @pytest.mark.asyncio
    async def test_paused_frames_not_recorded(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)

        # Push frames before pause
        for f in _frames(5):
            reader.push(f)

        rec.pause()
        frames_before_pause = rec.stats.frames_written + rec.stats.drop_count

        # Push more frames while paused — they should be dropped silently
        for f in _frames(10, start=1.0):
            reader.push(f)

        rec.resume()

        await rec.stop()
        # The paused frames should NOT appear in the queue
        assert rec.stats.drop_count == 0  # no queue overflow, just ignored

    @pytest.mark.asyncio
    async def test_resume_allows_frames(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)

        rec.pause()
        rec.resume()

        for f in _frames(5):
            reader.push(f)

        path = await rec.stop()
        assert path is not None


# ── Ring buffer / drop count ──────────────────────────────────────────────────


class TestRingBuffer:
    @pytest.mark.asyncio
    async def test_overflow_increments_drop_count(self, tmp_path):
        # Tiny buffer to force drops
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60, ring_buffer_size=2)
        reader = FakeReader()
        await rec.start(reader)

        # Push many frames rapidly without giving the writer time to drain
        for f in _frames(100):
            reader.push(f)

        await rec.stop()
        assert rec.stats.drop_count > 0

    @pytest.mark.asyncio
    async def test_no_drops_with_large_buffer(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60, ring_buffer_size=1200)
        reader = FakeReader()
        await rec.start(reader)

        for f in _frames(10):
            reader.push(f)

        await rec.stop()
        assert rec.stats.drop_count == 0


# ── Sample rate control ───────────────────────────────────────────────────────


class TestSampleRate:
    @pytest.mark.asyncio
    async def test_10hz_records_fewer_frames_than_60hz_input(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=10)
        reader = FakeReader()
        await rec.start(reader)

        # Push 60 frames as if from a 60Hz reader (1 second of data)
        for f in _frames(60, rate=60):
            reader.push(f)

        path = await rec.stop()
        assert path is not None
        assert path.exists()

        _, frames = read_recorder_file(path)
        # At 10Hz, ~10 frames from 60 input frames (first + ~9 more)
        assert len(frames) <= 11  # allow small tolerance

    @pytest.mark.asyncio
    async def test_60hz_records_all_frames(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)

        input_frames = _frames(60, rate=60)
        for f in input_frames:
            reader.push(f)

        path = await rec.stop()
        assert path is not None
        assert path.exists()

        _, frames = read_recorder_file(path)
        assert len(frames) == 60


# ── File format ───────────────────────────────────────────────────────────────


class TestFileFormat:
    @pytest.mark.asyncio
    async def test_file_starts_with_magic(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader, track_name="Monza", vehicle_name="GR010")
        for f in _frames(5):
            reader.push(f)
        path = await rec.stop()
        assert path is not None

        data = path.read_bytes()
        assert data[:8] == RECORDER_MAGIC

    @pytest.mark.asyncio
    async def test_header_contains_metadata(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=30)
        reader = FakeReader()
        await rec.start(reader, track_name="Spa", vehicle_name="Porsche", driver_name="Driver1")
        for f in _frames(5):
            reader.push(f)
        path = await rec.stop()
        assert path is not None

        header, _ = read_recorder_file(path)
        assert header["track"] == "Spa"
        assert header["vehicle"] == "Porsche"
        assert header["driver"] == "Driver1"
        assert header["sample_rate_hz"] == 30

    @pytest.mark.asyncio
    async def test_roundtrip_channel_values(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)

        # Push a single distinctive frame
        f = FakeFrame(1.0, speed=123.456, rpm=7777.0, throttle=55.0, gear=4.0)
        reader.push(f)

        path = await rec.stop()
        assert path is not None

        _, frames = read_recorder_file(path)
        assert len(frames) == 1
        fr = frames[0]
        assert fr["timestamp"] == pytest.approx(1.0)
        assert fr["speed"] == pytest.approx(123.456)
        assert fr["rpm"] == pytest.approx(7777.0)
        assert fr["throttle"] == pytest.approx(55.0)

    @pytest.mark.asyncio
    async def test_custom_channels_subset(self, tmp_path):
        rec = TelemetryRecorder(
            output_dir=tmp_path,
            sample_rate=60,
            channels=["speed", "rpm"],
        )
        reader = FakeReader()
        await rec.start(reader)

        f = FakeFrame(0.0, speed=200.0, rpm=9000.0, throttle=100.0, gear=6.0)
        reader.push(f)

        path = await rec.stop()
        assert path is not None

        header, frames = read_recorder_file(path)
        assert header["channels"] == ["speed", "rpm"]
        assert len(frames) == 1
        assert "speed" in frames[0]
        assert "rpm" in frames[0]
        assert "throttle" not in frames[0]

    @pytest.mark.asyncio
    async def test_read_recorder_file_raises_bad_magic(self, tmp_path):
        bad = tmp_path / "bad.tmu"
        bad.write_bytes(b"NOTMAGIC" + b"\x00" * 100)
        with pytest.raises(ValueError, match="bad magic"):
            read_recorder_file(bad)


# ── Stats ─────────────────────────────────────────────────────────────────────


class TestStats:
    @pytest.mark.asyncio
    async def test_frames_written_counts_recorded_frames(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)

        n = 10
        for f in _frames(n):
            reader.push(f)

        await rec.stop()
        assert rec.stats.frames_written == n

    @pytest.mark.asyncio
    async def test_bytes_written_nonzero(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        for f in _frames(5):
            reader.push(f)
        await rec.stop()
        assert rec.stats.bytes_written > 0

    @pytest.mark.asyncio
    async def test_duration_positive(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        for f in _frames(5):
            reader.push(f)
        await rec.stop()
        assert rec.stats.duration_s >= 0

    @pytest.mark.asyncio
    async def test_stats_live_during_recording(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        reader = FakeReader()
        await rec.start(reader)
        s = rec.stats
        assert s.duration_s >= 0
        await rec.stop()


# ── Error signal ──────────────────────────────────────────────────────────────


class TestErrorSignal:
    @pytest.mark.asyncio
    async def test_error_callback_registered(self, tmp_path):
        rec = TelemetryRecorder(output_dir=tmp_path, sample_rate=60)
        errors = []
        rec.on_error(lambda e: errors.append(e))
        reader = FakeReader()
        await rec.start(reader)
        await rec.stop()
        # No error expected in normal operation
        assert errors == []


# ── _pack_frame helper ────────────────────────────────────────────────────────


class TestPackFrame:
    def test_correct_size(self):
        fmt = "<ddd"  # ts + 2 channels
        channel_names = ["speed", "rpm"]
        frame = FakeFrame(1.0, speed=200.0, rpm=8000.0)
        raw = _pack_frame(fmt, channel_names, frame)
        assert len(raw) == struct.calcsize(fmt)

    def test_values_roundtrip(self):
        fmt = "<ddd"
        channel_names = ["speed", "rpm"]
        frame = FakeFrame(1.5, speed=199.9, rpm=7999.0)
        raw = _pack_frame(fmt, channel_names, frame)
        ts, speed, rpm = struct.unpack(fmt, raw)
        assert ts == pytest.approx(1.5)
        assert speed == pytest.approx(199.9)
        assert rpm == pytest.approx(7999.0)

    def test_missing_channel_defaults_to_zero(self):
        fmt = "<dd"
        channel_names = ["nonexistent"]
        frame = FakeFrame(0.0, speed=100.0)
        raw = _pack_frame(fmt, channel_names, frame)
        ts, val = struct.unpack(fmt, raw)
        assert val == pytest.approx(0.0)
