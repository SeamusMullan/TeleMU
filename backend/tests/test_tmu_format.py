"""Tests for the .tmu binary file format module."""

import json
import struct
import zlib

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
    TMUFooter,
    TMUHeader,
    build_minimal_tmu,
    compute_channel_offsets,
    frame_payload_size,
    pack_frame,
    unpack_frame,
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
