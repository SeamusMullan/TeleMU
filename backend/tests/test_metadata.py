"""Tests for session metadata and .tmu file handling."""

import json
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from telemu.models import SessionMetadata
from telemu.recording.metadata import decode_session_type, _decode_bytes
from telemu.recording.tmu_file import (
    MAGIC,
    FORMAT_VERSION,
    _HEADER_FMT,
    _HEADER_SIZE,
    read_header,
    write_header,
    update_metadata,
)


# ── SessionMetadata model tests ──────────────────────────────────────────────


class TestSessionMetadata:
    def test_defaults(self):
        meta = SessionMetadata()
        assert meta.track_name == ""
        assert meta.car_name == ""
        assert meta.car_class == ""
        assert meta.session_type == ""
        assert meta.driver_name == ""
        assert meta.car_number == 0
        assert meta.notes == ""
        assert meta.session_description == ""
        assert meta.setup_name == ""

    def test_full_construction(self):
        meta = SessionMetadata(
            track_name="Le Mans",
            car_name="Porsche 963",
            car_class="Hypercar",
            session_type="Race 1",
            driver_name="Max Verstappen",
            car_number=33,
            session_start_utc="2026-01-01T00:00:00+00:00",
            recording_start_utc="2026-01-01T00:01:00+00:00",
            recording_end_utc="2026-01-01T01:00:00+00:00",
            notes="Great lap in sector 2",
            session_description="Endurance practice",
            setup_name="low_downforce_v3",
        )
        assert meta.track_name == "Le Mans"
        assert meta.car_number == 33
        assert meta.notes == "Great lap in sector 2"

    def test_json_round_trip(self):
        meta = SessionMetadata(
            track_name="Spa",
            driver_name="Lando Norris",
            session_type="Qualifying 1",
        )
        data = json.loads(meta.model_dump_json())
        restored = SessionMetadata(**data)
        assert restored.track_name == "Spa"
        assert restored.driver_name == "Lando Norris"
        assert restored.session_type == "Qualifying 1"


# ── Metadata extraction helpers ──────────────────────────────────────────────


class TestDecodeSessionType:
    def test_known_types(self):
        assert decode_session_type(0) == "Test Day"
        assert decode_session_type(1) == "Practice 1"
        assert decode_session_type(5) == "Qualifying 1"
        assert decode_session_type(9) == "Warmup"
        assert decode_session_type(10) == "Race 1"
        assert decode_session_type(13) == "Race 4"

    def test_unknown_type(self):
        result = decode_session_type(99)
        assert "99" in result


class TestDecodeBytes:
    def test_normal_bytes(self):
        assert _decode_bytes(b"Le Mans\x00\x00\x00") == "Le Mans"

    def test_empty_bytes(self):
        assert _decode_bytes(b"\x00\x00") == ""

    def test_string_passthrough(self):
        assert _decode_bytes("already a string") == "already a string"


# ── .tmu file read/write tests ───────────────────────────────────────────────


class TestTmuFile:
    def _make_metadata(self, **overrides) -> SessionMetadata:
        defaults = dict(
            track_name="Monza",
            car_name="Ferrari 499P",
            car_class="Hypercar",
            session_type="Race 1",
            driver_name="Charles Leclerc",
            car_number=16,
            session_start_utc="2026-03-01T12:00:00+00:00",
            recording_start_utc="2026-03-01T12:01:00+00:00",
            recording_end_utc="2026-03-01T13:00:00+00:00",
            notes="",
            session_description="",
            setup_name="",
        )
        defaults.update(overrides)
        return SessionMetadata(**defaults)

    def test_write_and_read_header(self, tmp_path):
        path = tmp_path / "test.tmu"
        meta = self._make_metadata()
        write_header(path, meta, session_type_raw=10)

        restored = read_header(path)
        assert restored.track_name == "Monza"
        assert restored.car_name == "Ferrari 499P"
        assert restored.car_class == "Hypercar"
        assert restored.session_type == "Race 1"
        assert restored.driver_name == "Charles Leclerc"
        assert restored.car_number == 16

    def test_magic_number(self, tmp_path):
        path = tmp_path / "test.tmu"
        meta = self._make_metadata()
        write_header(path, meta)

        with open(path, "rb") as f:
            assert f.read(4) == MAGIC

    def test_invalid_magic_raises(self, tmp_path):
        path = tmp_path / "bad.tmu"
        path.write_bytes(b"XXXX" + b"\x00" * 200)
        with pytest.raises(ValueError, match="Invalid magic"):
            read_header(path)

    def test_truncated_file_raises(self, tmp_path):
        path = tmp_path / "short.tmu"
        path.write_bytes(b"TMU")  # too short
        with pytest.raises(ValueError, match="too small"):
            read_header(path)

    def test_update_notes(self, tmp_path):
        path = tmp_path / "test.tmu"
        meta = self._make_metadata()
        write_header(path, meta, session_type_raw=10)

        updated = update_metadata(path, notes="Great session!")
        assert updated.notes == "Great session!"
        assert updated.track_name == "Monza"  # unchanged

        # Re-read to confirm persistence
        reread = read_header(path)
        assert reread.notes == "Great session!"

    def test_update_multiple_fields(self, tmp_path):
        path = tmp_path / "test.tmu"
        meta = self._make_metadata()
        write_header(path, meta)

        updated = update_metadata(
            path,
            notes="Wet conditions",
            session_description="Rain race sim",
            setup_name="wet_setup_v2",
        )
        assert updated.notes == "Wet conditions"
        assert updated.session_description == "Rain race sim"
        assert updated.setup_name == "wet_setup_v2"

    def test_update_preserves_remaining_data(self, tmp_path):
        """Ensure data after the metadata block is preserved on update."""
        path = tmp_path / "test.tmu"
        meta = self._make_metadata()
        write_header(path, meta)

        # Append some fake frame data after the header
        fake_frames = b"\xDE\xAD\xBE\xEF" * 100
        with open(path, "ab") as f:
            f.write(fake_frames)

        update_metadata(path, notes="Updated")

        # Verify the fake frame data is still there
        with open(path, "rb") as f:
            fixed = f.read(_HEADER_SIZE)
            _, _, _, _, _, _, meta_len = struct.unpack(_HEADER_FMT, fixed)
            f.seek(_HEADER_SIZE + meta_len)
            remaining = f.read()

        assert remaining == fake_frames

    def test_header_version(self, tmp_path):
        path = tmp_path / "test.tmu"
        meta = self._make_metadata()
        write_header(path, meta)

        with open(path, "rb") as f:
            fixed = f.read(_HEADER_SIZE)
            _, version, *_ = struct.unpack(_HEADER_FMT, fixed)

        assert version == FORMAT_VERSION

    def test_unicode_metadata(self, tmp_path):
        path = tmp_path / "test.tmu"
        meta = self._make_metadata(
            driver_name="Sébastien Loeb",
            track_name="Nürburgring",
            notes="Très bien!",
        )
        write_header(path, meta)

        restored = read_header(path)
        assert restored.driver_name == "Sébastien Loeb"
        assert restored.track_name == "Nürburgring"
        assert restored.notes == "Très bien!"
