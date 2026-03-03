"""Tests for .tmu format and converter."""

import tempfile
from pathlib import Path

import duckdb
import pytest

from telemu.recording.tmu_format import TmuFrame, TmuHeader, read_tmu, write_tmu
from telemu.recording.converter import convert_tmu_to_duckdb, batch_convert


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sample_header() -> TmuHeader:
    return TmuHeader(
        track="Le Mans",
        session_type="Race",
        driver="Test Driver",
        vehicle="Porsche 963",
        date="2025-06-15",
        channels=["speed", "rpm", "throttle", "brake"],
    )


def _sample_frames(n: int = 50) -> list[TmuFrame]:
    frames = []
    for i in range(n):
        ts = i * 0.016
        frame = TmuFrame(
            ts=ts,
            channels={
                "speed": 100.0 + i,
                "rpm": 4000.0 + i * 10,
                "throttle": 50.0 + (i % 10),
                "brake": 10.0 + (i % 5),
            },
        )
        # Add lap markers every 10 frames
        if i > 0 and i % 10 == 0:
            frame.lap_marker = {
                "lap": i // 10,
                "last_time": f"1:{52 + i // 10}.000",
                "best_time": "1:52.000",
                "sectors": ["0:32.456", "0:38.789", "0:41.234"],
            }
        frames.append(frame)
    return frames


def _write_sample_tmu(path: Path, n_frames: int = 50) -> None:
    write_tmu(path, _sample_header(), _sample_frames(n_frames))


# ── .tmu format tests ────────────────────────────────────────────────────────


class TestTmuFormat:
    def test_roundtrip(self, tmp_path):
        tmu = tmp_path / "test.tmu"
        header = _sample_header()
        frames = _sample_frames(20)
        write_tmu(tmu, header, frames)

        hdr2, frames2 = read_tmu(tmu)
        assert hdr2.track == header.track
        assert hdr2.driver == header.driver
        assert len(frames2) == len(frames)
        assert frames2[0].ts == frames[0].ts
        assert frames2[0].channels["speed"] == frames[0].channels["speed"]

    def test_lap_markers_preserved(self, tmp_path):
        tmu = tmp_path / "test.tmu"
        frames = _sample_frames(20)
        write_tmu(tmu, _sample_header(), frames)

        _, frames2 = read_tmu(tmu)
        markers = [f for f in frames2 if f.lap_marker is not None]
        expected = [f for f in frames if f.lap_marker is not None]
        assert len(markers) == len(expected)
        assert markers[0].lap_marker["lap"] == expected[0].lap_marker["lap"]

    def test_bad_magic_raises(self, tmp_path):
        bad = tmp_path / "bad.tmu"
        bad.write_bytes(b"NOPE" + b"\x00" * 100)
        with pytest.raises(ValueError, match="bad magic"):
            read_tmu(bad)

    def test_empty_frames(self, tmp_path):
        tmu = tmp_path / "empty.tmu"
        write_tmu(tmu, TmuHeader(), [])
        hdr, frames = read_tmu(tmu)
        assert frames == []


# ── Converter tests ───────────────────────────────────────────────────────────


class TestConverter:
    def test_basic_conversion(self, tmp_path):
        tmu = tmp_path / "session.tmu"
        _write_sample_tmu(tmu)

        db_path = convert_tmu_to_duckdb(tmu)
        assert db_path.exists()

        conn = duckdb.connect(str(db_path), read_only=True)
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        assert "channels" in tables
        assert "lap_markers" in tables
        assert "metadata" in tables
        conn.close()
        db_path.unlink()

    def test_channels_table_columns(self, tmp_path):
        tmu = tmp_path / "session.tmu"
        _write_sample_tmu(tmu)

        db_path = convert_tmu_to_duckdb(tmu)
        conn = duckdb.connect(str(db_path), read_only=True)

        cols = [r[1] for r in conn.execute("PRAGMA table_info('channels')").fetchall()]
        assert "ts" in cols
        assert "speed" in cols
        assert "rpm" in cols
        assert "throttle" in cols
        assert "brake" in cols

        row_count = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        assert row_count == 50
        conn.close()
        db_path.unlink()

    def test_lap_markers_table(self, tmp_path):
        tmu = tmp_path / "session.tmu"
        _write_sample_tmu(tmu)

        db_path = convert_tmu_to_duckdb(tmu)
        conn = duckdb.connect(str(db_path), read_only=True)

        markers = conn.execute("SELECT * FROM lap_markers").fetchall()
        # Frames at indices 10, 20, 30, 40 have lap markers
        assert len(markers) == 4
        # First marker should be lap 1
        assert markers[0][1] == 1
        conn.close()
        db_path.unlink()

    def test_metadata_table(self, tmp_path):
        tmu = tmp_path / "session.tmu"
        _write_sample_tmu(tmu)

        db_path = convert_tmu_to_duckdb(tmu)
        conn = duckdb.connect(str(db_path), read_only=True)

        rows = conn.execute("SELECT * FROM metadata").fetchall()
        meta = {r[0]: r[1] for r in rows}
        assert meta["track"] == "Le Mans"
        assert meta["session_type"] == "Race"
        assert meta["driver"] == "Test Driver"
        assert meta["vehicle"] == "Porsche 963"
        conn.close()
        db_path.unlink()

    def test_custom_output_path(self, tmp_path):
        tmu = tmp_path / "input.tmu"
        _write_sample_tmu(tmu)

        out = tmp_path / "output.duckdb"
        result = convert_tmu_to_duckdb(tmu, out)
        assert result == out
        assert out.exists()
        out.unlink()

    def test_progress_callback(self, tmp_path):
        tmu = tmp_path / "session.tmu"
        _write_sample_tmu(tmu, n_frames=100)

        progress_calls: list[tuple[int, int]] = []
        convert_tmu_to_duckdb(tmu, on_progress=lambda cur, tot: progress_calls.append((cur, tot)))

        # Should have been called at least once
        assert len(progress_calls) > 0
        # Last call should be (total, total)
        assert progress_calls[-1][0] == progress_calls[-1][1]
        tmu.with_suffix(".duckdb").unlink()

    def test_batch_convert(self, tmp_path):
        paths = []
        for i in range(3):
            p = tmp_path / f"session_{i}.tmu"
            _write_sample_tmu(p, n_frames=10)
            paths.append(p)

        results = batch_convert(paths, output_dir=tmp_path)
        assert len(results) == 3
        for r in results:
            assert r.exists()
            conn = duckdb.connect(str(r), read_only=True)
            tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
            assert "channels" in tables
            conn.close()
            r.unlink()

    def test_empty_tmu_conversion(self, tmp_path):
        tmu = tmp_path / "empty.tmu"
        write_tmu(tmu, TmuHeader(track="Empty"), [])

        db_path = convert_tmu_to_duckdb(tmu)
        conn = duckdb.connect(str(db_path), read_only=True)

        row_count = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        assert row_count == 0

        markers = conn.execute("SELECT COUNT(*) FROM lap_markers").fetchone()[0]
        assert markers == 0

        meta = dict(conn.execute("SELECT * FROM metadata").fetchall())
        assert meta["track"] == "Empty"
        conn.close()
        db_path.unlink()
