"""Tests for the .tmu binary file format module and integrity verification."""

import json
import struct
import zlib
from pathlib import Path

import pytest

from telemu.recording.tmu_format import (
    CHANNEL_DEF_FMT,
    CHANNEL_DEF_SIZE,
    FOOTER_FMT,
    FOOTER_SIZE,
    FORMAT_VERSION,
    FRAME_HEADER_FMT,
    FRAME_HEADER_SIZE,
    HEADER_FIXED_SIZE,
    HEADER_FMT,
    MAGIC,
    ChannelDef,
    ChannelType,
    TMUCorruptionError,
    TMUFooter,
    TMUHeader,
    VerifyResult,
    build_minimal_tmu,
    compute_channel_offsets,
    frame_payload_size,
    pack_frame,
    repair_file,
    repair_tmu,
    unpack_frame,
    verify_file,
    verify_tmu,
)


# ── Constant sanity checks ───────────────────────────────────────────────────


def test_struct_sizes():
    """Verify that declared sizes match struct.calcsize."""
    assert struct.calcsize(HEADER_FMT) == HEADER_FIXED_SIZE
    assert struct.calcsize(CHANNEL_DEF_FMT) == CHANNEL_DEF_SIZE
    assert struct.calcsize(FRAME_HEADER_FMT) == FRAME_HEADER_SIZE
    assert struct.calcsize(FOOTER_FMT) == FOOTER_SIZE


def test_magic_bytes():
    assert MAGIC == b"TMU\x01"
    assert FORMAT_VERSION == 1


# ── ChannelType ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ct, size, char",
    [
        (ChannelType.FLOAT64, 8, "d"),
        (ChannelType.FLOAT32, 4, "f"),
        (ChannelType.INT32, 4, "i"),
        (ChannelType.UINT16, 2, "H"),
        (ChannelType.BOOL, 1, "?"),
    ],
)
def test_channel_type_properties(ct, size, char):
    assert ct.size == size
    assert ct.struct_char == char


# ── ChannelDef round-trip ─────────────────────────────────────────────────────


def test_channel_def_pack_unpack():
    ch = ChannelDef("speed", ChannelType.FLOAT64, "km/h", byte_offset=0)
    raw = ch.pack()
    assert len(raw) == CHANNEL_DEF_SIZE
    ch2 = ChannelDef.unpack(raw)
    assert ch2.name == "speed"
    assert ch2.channel_type == ChannelType.FLOAT64
    assert ch2.unit == "km/h"
    assert ch2.byte_offset == 0


def test_channel_def_truncates_long_name():
    """Names longer than 32 bytes are silently truncated."""
    long_name = "a" * 50
    ch = ChannelDef(long_name, ChannelType.FLOAT32, "unit", byte_offset=0)
    ch2 = ChannelDef.unpack(ch.pack())
    assert len(ch2.name) == 32


# ── TMUHeader round-trip ─────────────────────────────────────────────────────


def test_header_pack_unpack():
    meta = json.dumps({"weather": "sunny"}).encode()
    hdr = TMUHeader(
        track_name="Spa",
        vehicle_name="Toyota GR010",
        driver_name="Driver1",
        session_type=2,
        channel_count=5,
        created_at=1700000000.0,
        metadata_json=meta,
    )
    raw = hdr.pack()
    # Fixed part + metadata
    assert len(raw) == HEADER_FIXED_SIZE + len(meta)

    hdr2 = TMUHeader.unpack(raw)
    assert hdr2.track_name == "Spa"
    assert hdr2.vehicle_name == "Toyota GR010"
    assert hdr2.driver_name == "Driver1"
    assert hdr2.session_type == 2
    assert hdr2.channel_count == 5
    assert hdr2.created_at == 1700000000.0
    assert hdr2.metadata_json == meta
    assert hdr2.version == FORMAT_VERSION


def test_header_rejects_bad_magic():
    raw = b"BAD!" + b"\x00" * (HEADER_FIXED_SIZE - 4 + 2)
    with pytest.raises(ValueError, match="Bad magic"):
        TMUHeader.unpack(raw)


def test_header_rejects_short_data():
    with pytest.raises(ValueError, match="too short"):
        TMUHeader.unpack(b"\x00" * 10)


# ── TMUFooter round-trip ─────────────────────────────────────────────────────


def test_footer_pack_unpack():
    ft = TMUFooter(frame_count=100, index_offset=4096, checksum=0xDEADBEEF)
    raw = ft.pack()
    assert len(raw) == FOOTER_SIZE
    ft2 = TMUFooter.unpack(raw)
    assert ft2.frame_count == 100
    assert ft2.index_offset == 4096
    assert ft2.checksum == 0xDEADBEEF


# ── Frame pack / unpack ──────────────────────────────────────────────────────


def test_frame_round_trip():
    channels = [
        ChannelDef("speed", ChannelType.FLOAT64, "km/h", 0),
        ChannelDef("gear", ChannelType.INT32, "", 8),
        ChannelDef("drs", ChannelType.BOOL, "", 12),
    ]
    compute_channel_offsets(channels)

    values = [
        (ChannelType.FLOAT64, 210.5),
        (ChannelType.INT32, 4),
        (ChannelType.BOOL, True),
    ]
    raw = pack_frame(1.234, values)
    assert len(raw) == frame_payload_size(channels)

    ts, decoded = unpack_frame(raw, channels)
    assert ts == pytest.approx(1.234)
    assert decoded["speed"] == pytest.approx(210.5)
    assert decoded["gear"] == 4
    assert decoded["drs"] is True


# ── compute_channel_offsets ───────────────────────────────────────────────────


def test_compute_channel_offsets():
    channels = [
        ChannelDef("a", ChannelType.FLOAT64, "", 0),
        ChannelDef("b", ChannelType.FLOAT32, "", 0),
        ChannelDef("c", ChannelType.BOOL, "", 0),
    ]
    compute_channel_offsets(channels)
    assert channels[0].byte_offset == 0
    assert channels[1].byte_offset == 8   # after FLOAT64
    assert channels[2].byte_offset == 12  # after FLOAT64 + FLOAT32


# ── build_minimal_tmu ────────────────────────────────────────────────────────


def test_build_minimal_tmu_is_valid():
    """The built file can be parsed back: header → channels → frames → footer."""
    data = build_minimal_tmu()
    assert data[:4] == MAGIC

    # Parse header
    hdr = TMUHeader.unpack(data)
    assert hdr.track_name == "Monza"
    assert hdr.vehicle_name == "Porsche 963"
    assert hdr.channel_count == 3

    # Parse channel defs
    ch_start = HEADER_FIXED_SIZE + len(hdr.metadata_json)
    channels = []
    for i in range(hdr.channel_count):
        offset = ch_start + i * CHANNEL_DEF_SIZE
        channels.append(ChannelDef.unpack(data[offset : offset + CHANNEL_DEF_SIZE]))
    assert [c.name for c in channels] == ["speed", "rpm", "gear"]

    # Parse footer
    footer = TMUFooter.unpack(data[-FOOTER_SIZE:])
    assert footer.frame_count == 2

    # Verify CRC-32
    expected_crc = zlib.crc32(data[: -FOOTER_SIZE]) & 0xFFFFFFFF
    assert footer.checksum == expected_crc

    # Parse frames via index
    idx_start = footer.index_offset
    fsize = frame_payload_size(channels)
    for i in range(footer.frame_count):
        (frame_offset,) = struct.unpack("<Q", data[idx_start + i * 8 : idx_start + i * 8 + 8])
        frame_data = data[frame_offset : frame_offset + fsize]
        ts, vals = unpack_frame(frame_data, channels)
        assert isinstance(ts, float)
        assert "speed" in vals


# ── Edge case: empty recording ───────────────────────────────────────────────


def test_empty_recording_valid():
    """A .tmu file with zero frames should still be valid and parseable."""
    channels = [
        ChannelDef("speed", ChannelType.FLOAT64, "km/h", 0),
        ChannelDef("rpm", ChannelType.FLOAT64, "rpm", 8),
    ]
    compute_channel_offsets(channels)
    data = build_minimal_tmu(channels=channels, frames=[])

    assert data[:4] == MAGIC

    footer = TMUFooter.unpack(data[-FOOTER_SIZE:])
    assert footer.frame_count == 0

    result = verify_tmu(data)
    assert result.ok is True
    assert result.frame_count == 0


# ── Edge case: single frame ───────────────────────────────────────────────────


def test_single_frame_roundtrip():
    """A .tmu file with exactly one frame should round-trip correctly."""
    channels = [
        ChannelDef("speed", ChannelType.FLOAT64, "km/h", 0),
        ChannelDef("gear", ChannelType.INT32, "", 8),
    ]
    compute_channel_offsets(channels)
    frames = [(42.0, [(ChannelType.FLOAT64, 199.9), (ChannelType.INT32, 6)])]
    data = build_minimal_tmu(channels=channels, frames=frames)

    result = verify_tmu(data)
    assert result.ok is True
    assert result.frame_count == 1

    footer = TMUFooter.unpack(data[-FOOTER_SIZE:])
    hdr = TMUHeader.unpack(data)
    (frame_offset,) = struct.unpack(
        "<Q", data[footer.index_offset : footer.index_offset + 8]
    )
    fsize = frame_payload_size(channels)
    ts, vals = unpack_frame(data[frame_offset : frame_offset + fsize], channels)
    assert ts == pytest.approx(42.0)
    assert vals["speed"] == pytest.approx(199.9)
    assert vals["gear"] == 6


# ── Edge case: max channel types ─────────────────────────────────────────────


def test_all_channel_types_roundtrip():
    """A frame with one channel of each ChannelType should round-trip correctly."""
    channels = [
        ChannelDef("f64", ChannelType.FLOAT64, "unit", 0),
        ChannelDef("f32", ChannelType.FLOAT32, "unit", 0),
        ChannelDef("i32", ChannelType.INT32, "unit", 0),
        ChannelDef("u16", ChannelType.UINT16, "unit", 0),
        ChannelDef("boo", ChannelType.BOOL, "unit", 0),
    ]
    compute_channel_offsets(channels)

    values = [
        (ChannelType.FLOAT64, 1.23456789),
        (ChannelType.FLOAT32, 2.5),
        (ChannelType.INT32, -42),
        (ChannelType.UINT16, 65535),
        (ChannelType.BOOL, True),
    ]
    frames = [(0.016, values)]
    data = build_minimal_tmu(channels=channels, frames=frames)

    result = verify_tmu(data)
    assert result.ok is True
    assert result.frame_count == 1

    footer = TMUFooter.unpack(data[-FOOTER_SIZE:])
    (frame_offset,) = struct.unpack(
        "<Q", data[footer.index_offset : footer.index_offset + 8]
    )
    fsize = frame_payload_size(channels)
    ts, vals = unpack_frame(data[frame_offset : frame_offset + fsize], channels)
    assert ts == pytest.approx(0.016)
    assert vals["f64"] == pytest.approx(1.23456789)
    assert vals["f32"] == pytest.approx(2.5, abs=1e-5)
    assert vals["i32"] == -42
    assert vals["u16"] == 65535
    assert vals["boo"] is True


# ── Integrity verification tests ─────────────────────────────────────────────


@pytest.fixture
def valid_tmu_data() -> bytes:
    """Build a valid .tmu byte string for verification tests."""
    return build_minimal_tmu()


@pytest.fixture
def valid_tmu_file(tmp_path: Path, valid_tmu_data: bytes) -> Path:
    """Write a valid .tmu file and return its path."""
    p = tmp_path / "test.tmu"
    p.write_bytes(valid_tmu_data)
    return p


def test_verify_ok(valid_tmu_data: bytes):
    """A freshly built file passes verification."""
    result = verify_tmu(valid_tmu_data)
    assert result.ok is True
    assert result.crc32_ok is True
    assert result.header_ok is True
    assert result.frame_count == 2


def test_verify_file_ok(valid_tmu_file: Path):
    """verify_file works on disk."""
    result = verify_file(valid_tmu_file)
    assert result.ok is True
    assert result.frame_count == 2


def test_verify_crc32_mismatch(valid_tmu_data: bytes):
    """Tampering with body bytes should break the CRC-32 check."""
    corrupted = bytearray(valid_tmu_data)
    corrupted[10] ^= 0xFF  # flip a byte in the header region
    result = verify_tmu(bytes(corrupted))
    assert result.ok is False
    assert result.crc32_ok is False
    assert "CRC-32 mismatch" in result.message


def test_verify_bad_magic():
    """File with wrong magic should fail verification."""
    data = b"BAAD" + b"\x00" * (HEADER_FIXED_SIZE + FOOTER_SIZE)
    result = verify_tmu(data)
    assert result.ok is False
    assert result.header_ok is False
    assert "Bad magic" in result.message


def test_verify_too_small():
    """File too small should fail verification."""
    result = verify_tmu(b"tiny")
    assert result.ok is False
    assert "File too small" in result.message


# ── Repair tests ─────────────────────────────────────────────────────────────


def test_repair_corrupted_crc(valid_tmu_data: bytes):
    """Repair should recover frames from a file with corrupted CRC."""
    corrupted = bytearray(valid_tmu_data)
    # Corrupt a byte in the body (but NOT in frame data itself)
    # Flip a metadata byte that won't affect frame parsing
    corrupted[10] ^= 0xFF
    result = verify_tmu(bytes(corrupted))
    assert result.ok is False

    repaired, recovered, skipped = repair_tmu(bytes(corrupted))
    # The repaired file should be valid
    result2 = verify_tmu(repaired)
    assert result2.ok is True
    assert recovered == 2


def test_repair_file(valid_tmu_file: Path, tmp_path: Path):
    """repair_file should write a valid file from a corrupted source."""
    data = bytearray(valid_tmu_file.read_bytes())
    data[10] ^= 0xFF
    valid_tmu_file.write_bytes(bytes(data))

    out = tmp_path / "repaired.tmu"
    recovered, skipped = repair_file(valid_tmu_file, out)
    assert recovered == 2
    assert out.exists()

    result = verify_file(out)
    assert result.ok is True


def test_repair_too_small():
    """Repair should raise on a file too small to parse."""
    with pytest.raises(TMUCorruptionError, match="too small"):
        repair_tmu(b"tiny")


# ── CLI tests ────────────────────────────────────────────────────────────────


def test_verify_cli_ok(valid_tmu_file: Path):
    """CLI verify should exit 0 for a valid file."""
    from telemu.recording.verify import main

    rc = main([str(valid_tmu_file)])
    assert rc == 0


def test_verify_cli_corrupted(valid_tmu_file: Path):
    """CLI verify should exit 2 for a corrupted file."""
    data = bytearray(valid_tmu_file.read_bytes())
    data[10] ^= 0xFF
    valid_tmu_file.write_bytes(bytes(data))

    from telemu.recording.verify import main

    rc = main([str(valid_tmu_file)])
    assert rc == 2


def test_verify_cli_repair(valid_tmu_file: Path):
    """CLI verify --repair should recover frames."""
    data = bytearray(valid_tmu_file.read_bytes())
    data[10] ^= 0xFF
    valid_tmu_file.write_bytes(bytes(data))

    repaired_path = valid_tmu_file.with_suffix(".repaired.tmu")
    try:
        from telemu.recording.verify import main

        rc = main([str(valid_tmu_file), "--repair"])
        assert rc == 0
        assert repaired_path.exists()
    finally:
        repaired_path.unlink(missing_ok=True)


def test_verify_cli_file_not_found():
    """CLI should exit 1 for a missing file."""
    from telemu.recording.verify import main

    rc = main(["/tmp/nonexistent.tmu"])
    assert rc == 1
