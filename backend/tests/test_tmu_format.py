"""Tests for TMU file format integrity verification."""

import struct
import zlib
from pathlib import Path

import pytest

from telemu.recording.tmu_format import (
    CHUNK_HEADER_STRUCT,
    FOOTER_STRUCT,
    TMUCorruptionError,
    TMUHeader,
    TMUReader,
    TMUWriter,
    VerifyResult,
    repair_file,
    verify_file,
)


@pytest.fixture
def sample_frames() -> list[bytes]:
    """Return a few small raw frames for testing."""
    return [
        b"frame-000-" + bytes(range(256)),
        b"frame-001-" + bytes(range(256)),
        b"frame-002-" + bytes(range(256)),
    ]


@pytest.fixture
def tmu_path(tmp_path: Path, sample_frames: list[bytes]) -> Path:
    """Write a valid .tmu file and return its path."""
    tmp = tmp_path / "test.tmu"
    header = TMUHeader(
        created_at=1700000000.0,
        track_name="Spa-Francorchamps",
        vehicle_name="Porsche 963",
        session_type=2,
        metadata=b'{"driver":"Test"}',
    )
    with TMUWriter(tmp, header) as w:
        for f in sample_frames:
            w.write_frame(f)
    return tmp


# ── Round-trip tests ─────────────────────────────────────────────────────────


def test_roundtrip(tmu_path: Path, sample_frames: list[bytes]):
    """Frames written then read back must be identical."""
    with TMUReader(tmu_path) as r:
        assert r.frame_count == 3
        for i, expected in enumerate(sample_frames):
            assert r.read_frame(i) == expected


def test_header_fields(tmu_path: Path):
    """Header metadata survives round-trip."""
    with TMUReader(tmu_path) as r:
        assert r.header.track_name == "Spa-Francorchamps"
        assert r.header.vehicle_name == "Porsche 963"
        assert r.header.session_type == 2
        assert r.header.created_at == 1700000000.0
        assert r.header.metadata == b'{"driver":"Test"}'


def test_read_all_frames(tmu_path: Path, sample_frames: list[bytes]):
    with TMUReader(tmu_path) as r:
        all_frames = r.read_all_frames()
        assert all_frames == sample_frames


# ── Verification tests ───────────────────────────────────────────────────────


def test_verify_ok(tmu_path: Path):
    """A freshly written file passes verification."""
    result = verify_file(tmu_path)
    assert result.ok is True
    assert result.sha256_ok is True
    assert result.chunk_errors == []
    assert result.frame_count == 3


def test_verify_sha256_mismatch(tmu_path: Path):
    """Tampering with the header should break the SHA-256 check."""
    data = tmu_path.read_bytes()
    # Flip a byte in the header region
    corrupted = bytearray(data)
    corrupted[10] ^= 0xFF
    tmu_path.write_bytes(bytes(corrupted))

    result = verify_file(tmu_path)
    assert result.ok is False
    assert result.sha256_ok is False


def test_verify_crc32_mismatch(tmu_path: Path):
    """Corrupting a compressed chunk should trigger a CRC32 error."""
    data = bytearray(tmu_path.read_bytes())

    # Read footer to find the frame index
    footer_data = data[-FOOTER_STRUCT.size:]
    frame_count, index_offset, _sha = FOOTER_STRUCT.unpack(footer_data)

    # Read offset of frame 1
    idx_start = index_offset + 8  # skip frame 0's offset
    (frame1_offset,) = struct.unpack("<Q", data[idx_start : idx_start + 8])

    # Corrupt one byte inside the compressed data of frame 1
    corrupt_pos = frame1_offset + CHUNK_HEADER_STRUCT.size + 1
    data[corrupt_pos] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    result = verify_file(tmu_path)
    assert result.ok is False
    assert 1 in result.chunk_errors


def test_reader_raises_on_corrupted_file(tmu_path: Path):
    """TMUReader(verify=True) should raise on a corrupted file."""
    data = bytearray(tmu_path.read_bytes())
    data[10] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    with pytest.raises(TMUCorruptionError):
        TMUReader(tmu_path, verify=True)


def test_reader_skip_verify(tmu_path: Path):
    """TMUReader(verify=False) should open even a corrupted file."""
    data = bytearray(tmu_path.read_bytes())
    data[10] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    with TMUReader(tmu_path, verify=False) as r:
        assert r.frame_count == 3


def test_read_frame_crc_check(tmu_path: Path, sample_frames: list[bytes]):
    """read_frame should raise on a per-chunk CRC mismatch."""
    data = bytearray(tmu_path.read_bytes())

    # Find frame 0 offset
    footer_data = data[-FOOTER_STRUCT.size:]
    _fc, index_offset, _sha = FOOTER_STRUCT.unpack(footer_data)
    (frame0_offset,) = struct.unpack("<Q", data[index_offset : index_offset + 8])

    # Corrupt compressed data of frame 0
    corrupt_pos = frame0_offset + CHUNK_HEADER_STRUCT.size + 1
    data[corrupt_pos] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    with TMUReader(tmu_path, verify=False) as r:
        with pytest.raises(TMUCorruptionError, match="CRC32 mismatch"):
            r.read_frame(0)


def test_read_all_frames_skip_corrupted(tmu_path: Path, sample_frames: list[bytes]):
    """read_all_frames(skip_corrupted=True) should skip bad chunks."""
    data = bytearray(tmu_path.read_bytes())

    # Corrupt frame 1
    footer_data = data[-FOOTER_STRUCT.size:]
    _fc, index_offset, _sha = FOOTER_STRUCT.unpack(footer_data)
    idx_start = index_offset + 8
    (frame1_offset,) = struct.unpack("<Q", data[idx_start : idx_start + 8])
    corrupt_pos = frame1_offset + CHUNK_HEADER_STRUCT.size + 1
    data[corrupt_pos] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    with TMUReader(tmu_path, verify=False) as r:
        frames = r.read_all_frames(skip_corrupted=True)
        # Frame 0 and frame 2 should survive
        assert len(frames) == 2
        assert frames[0] == sample_frames[0]
        assert frames[1] == sample_frames[2]


# ── Repair tests ─────────────────────────────────────────────────────────────


def test_repair(tmu_path: Path, sample_frames: list[bytes]):
    """Repair should recover valid frames from a corrupted file."""
    data = bytearray(tmu_path.read_bytes())

    # Corrupt frame 1
    footer_data = data[-FOOTER_STRUCT.size:]
    _fc, index_offset, _sha = FOOTER_STRUCT.unpack(footer_data)
    idx_start = index_offset + 8
    (frame1_offset,) = struct.unpack("<Q", data[idx_start : idx_start + 8])
    corrupt_pos = frame1_offset + CHUNK_HEADER_STRUCT.size + 1
    data[corrupt_pos] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    repaired_path = tmu_path.with_suffix(".repaired.tmu")
    try:
        recovered, skipped = repair_file(tmu_path, repaired_path)
        assert recovered == 2
        assert skipped == 1

        # Repaired file should pass verification
        result = verify_file(repaired_path)
        assert result.ok is True
        assert result.frame_count == 2

        # Content should match frames 0 and 2
        with TMUReader(repaired_path) as r:
            assert r.read_frame(0) == sample_frames[0]
            assert r.read_frame(1) == sample_frames[2]
    finally:
        repaired_path.unlink(missing_ok=True)


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_empty_file(tmp_path: Path):
    """Verification should fail gracefully on a tiny file."""
    tmp = tmp_path / "tiny.tmu"
    tmp.write_bytes(b"tiny")
    result = verify_file(tmp)
    assert result.ok is False


def test_bad_magic(tmp_path: Path):
    """File with wrong magic should fail verification."""
    tmp = tmp_path / "bad.tmu"
    tmp.write_bytes(b"BAAD" + b"\x00" * 200)
    result = verify_file(tmp)
    assert result.ok is False
    assert "Bad magic" in result.message


def test_frame_index_out_of_range(tmu_path: Path):
    """Accessing an out-of-range frame should raise IndexError."""
    with TMUReader(tmu_path) as r:
        with pytest.raises(IndexError):
            r.read_frame(99)
        with pytest.raises(IndexError):
            r.read_frame(-1)


def test_zero_frames(tmp_path: Path):
    """A .tmu file with zero frames should still verify."""
    tmp = tmp_path / "empty.tmu"
    header = TMUHeader(track_name="Empty", vehicle_name="None")
    with TMUWriter(tmp, header) as w:
        pass  # no frames
    result = verify_file(tmp)
    assert result.ok is True
    assert result.frame_count == 0


# ── CLI tests ────────────────────────────────────────────────────────────────


def test_verify_cli_ok(tmu_path: Path):
    """CLI verify should exit 0 for a valid file."""
    from telemu.recording.verify import main

    rc = main([str(tmu_path)])
    assert rc == 0


def test_verify_cli_corrupted(tmu_path: Path):
    """CLI verify should exit 2 for a corrupted file."""
    data = bytearray(tmu_path.read_bytes())
    data[10] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    from telemu.recording.verify import main

    rc = main([str(tmu_path)])
    assert rc == 2


def test_verify_cli_repair(tmu_path: Path, sample_frames: list[bytes]):
    """CLI verify --repair should recover frames."""
    data = bytearray(tmu_path.read_bytes())

    # Corrupt frame 1
    footer_data = data[-FOOTER_STRUCT.size:]
    _fc, index_offset, _sha = FOOTER_STRUCT.unpack(footer_data)
    idx_start = index_offset + 8
    (frame1_offset,) = struct.unpack("<Q", data[idx_start : idx_start + 8])
    corrupt_pos = frame1_offset + CHUNK_HEADER_STRUCT.size + 1
    data[corrupt_pos] ^= 0xFF
    tmu_path.write_bytes(bytes(data))

    repaired_path = tmu_path.with_suffix(".repaired.tmu")
    try:
        from telemu.recording.verify import main

        rc = main([str(tmu_path), "--repair"])
        assert rc == 0
        assert repaired_path.exists()
    finally:
        repaired_path.unlink(missing_ok=True)


def test_verify_cli_file_not_found():
    """CLI should exit 1 for a missing file."""
    from telemu.recording.verify import main

    rc = main(["/tmp/nonexistent.tmu"])
    assert rc == 1
