"""Tests for the telemetry streaming client and protocol."""

from __future__ import annotations

import struct
import time

import pytest

from telemu.streaming.protocol import (
    MAGIC,
    MSG_DISCOVERY,
    MSG_PING,
    MSG_PONG,
    MSG_WELCOME,
    PROTOCOL_VERSION,
    UDP_HDR_FMT,
    UDP_HDR_SIZE,
    UDP_CH_FMT,
    UDP_CH_SIZE,
    CTRL_HDR,
    CTRL_HDR_SIZE,
    DISCOVERY_FMT,
    DISCOVERY_SIZE,
    CHANNEL_ENTRY_FMT,
    CHANNEL_ENTRY_SIZE,
    WELCOME_BASE_FMT,
    pack_ctrl,
    pack_hello,
    pack_pong,
    pack_subscribe,
    parse_udp_frame,
    parse_discovery,
)
from telemu.streaming.client import (
    STATE_CONNECTED,
    STATE_IDLE,
    StreamingClient,
    _parse_channel_list,
)


# ── Protocol struct / helper tests ────────────────────────────────────────────


def test_magic_constant():
    assert MAGIC == b"TMU\x02"
    assert len(MAGIC) == 4


def test_protocol_version():
    assert PROTOCOL_VERSION == 1


def test_udp_header_size():
    assert UDP_HDR_SIZE == 22  # 4+4+4+8+2


def test_channel_entry_size():
    assert CHANNEL_ENTRY_SIZE == 67  # 2+32+16+1+8+8


def test_ctrl_header_size():
    assert CTRL_HDR_SIZE == 7  # 4+2+1


# ── pack_ctrl ─────────────────────────────────────────────────────────────────


def test_pack_ctrl_empty_payload():
    msg = pack_ctrl(MSG_PING, b"")
    assert len(msg) == CTRL_HDR_SIZE
    magic, length, msg_type = CTRL_HDR.unpack(msg)
    assert magic == MAGIC
    assert length == 0
    assert msg_type == MSG_PING


def test_pack_ctrl_with_payload():
    payload = b"\x01\x02\x03"
    msg = pack_ctrl(0x10, payload)
    assert len(msg) == CTRL_HDR_SIZE + 3
    magic, length, msg_type = CTRL_HDR.unpack(msg[:CTRL_HDR_SIZE])
    assert magic == MAGIC
    assert length == 3
    assert msg_type == 0x10
    assert msg[CTRL_HDR_SIZE:] == payload


# ── pack_hello ────────────────────────────────────────────────────────────────


def test_pack_hello():
    msg = pack_hello("test-client")
    assert len(msg) >= CTRL_HDR_SIZE
    magic, length, msg_type = CTRL_HDR.unpack(msg[:CTRL_HDR_SIZE])
    assert magic == MAGIC
    assert msg_type == 0x10  # MSG_HELLO
    assert length == 34      # 32 + 2


# ── pack_subscribe ────────────────────────────────────────────────────────────


def test_pack_subscribe_all_channels():
    msg = pack_subscribe(8, subscribe_all=True)
    magic, length, msg_type = CTRL_HDR.unpack(msg[:CTRL_HDR_SIZE])
    assert msg_type == 0x12  # MSG_SUBSCRIBE
    assert length == 1       # ceil(8/8) = 1 byte
    assert msg[CTRL_HDR_SIZE] == 0xFF


def test_pack_subscribe_no_channels():
    msg = pack_subscribe(8, subscribe_all=False)
    magic, length, msg_type = CTRL_HDR.unpack(msg[:CTRL_HDR_SIZE])
    assert msg_type == 0x12
    assert msg[CTRL_HDR_SIZE] == 0x00


# ── pack_pong ─────────────────────────────────────────────────────────────────


def test_pack_pong():
    ts = 1234.567
    msg = pack_pong(ts)
    magic, length, msg_type = CTRL_HDR.unpack(msg[:CTRL_HDR_SIZE])
    assert msg_type == 0x16  # MSG_PONG
    assert length == 8
    (echo_ts,) = struct.unpack("<d", msg[CTRL_HDR_SIZE:])
    assert abs(echo_ts - ts) < 1e-9


# ── parse_udp_frame ───────────────────────────────────────────────────────────


def _make_udp_frame(seq: int, ts: float, channels: dict[int, float]) -> bytes:
    """Build a valid UDP telemetry frame."""
    ch_count = len(channels)
    hdr = UDP_HDR_FMT.pack(MAGIC, 0, seq, ts, ch_count)
    payload = b"".join(
        UDP_CH_FMT.pack(ch_id, value) for ch_id, value in channels.items()
    )
    return hdr + payload


def test_parse_udp_frame_valid():
    frame = _make_udp_frame(seq=7, ts=2.5, channels={0: 100.0, 1: 5000.0})
    result = parse_udp_frame(frame)
    assert result is not None
    _sid, seq, ts, channels = result
    assert seq == 7
    assert abs(ts - 2.5) < 1e-9
    assert channels["0"] == pytest.approx(100.0)
    assert channels["1"] == pytest.approx(5000.0)


def test_parse_udp_frame_bad_magic():
    frame = _make_udp_frame(seq=0, ts=0.0, channels={0: 1.0})
    bad = b"XXXX" + frame[4:]
    assert parse_udp_frame(bad) is None


def test_parse_udp_frame_too_short():
    assert parse_udp_frame(b"\x00" * 10) is None


def test_parse_udp_frame_truncated_channels():
    """Declared channel_count exceeds available bytes → None."""
    # Build header claiming 5 channels but provide 0 channel data
    hdr = UDP_HDR_FMT.pack(MAGIC, 0, 1, 1.0, 5)
    assert parse_udp_frame(hdr) is None


# ── parse_discovery ───────────────────────────────────────────────────────────


def _make_discovery_pkt(
    driver="Driver",
    track="Track",
    vehicle="Car",
    tcp_port=9101,
    udp_port=9100,
    session_id=42,
) -> bytes:
    drv_b = driver.encode().ljust(32, b"\x00")
    trk_b = track.encode().ljust(64, b"\x00")
    veh_b = vehicle.encode().ljust(64, b"\x00")
    return DISCOVERY_FMT.pack(
        MAGIC, 1, MSG_DISCOVERY, drv_b, trk_b, veh_b, 0, tcp_port, udp_port, session_id
    )


def test_parse_discovery_valid():
    pkt = _make_discovery_pkt(driver="Seamus", track="Monza", tcp_port=9101)
    info = parse_discovery(pkt)
    assert info is not None
    assert info["driver_name"] == "Seamus"
    assert info["track_name"] == "Monza"
    assert info["tcp_port"] == 9101
    assert info["udp_port"] == 9100


def test_parse_discovery_bad_magic():
    pkt = _make_discovery_pkt()
    bad = b"XXXX" + pkt[4:]
    assert parse_discovery(bad) is None


def test_parse_discovery_too_short():
    assert parse_discovery(b"\x00" * 10) is None


# ── _parse_channel_list ───────────────────────────────────────────────────────


def _make_channel_list(names: list[str]) -> bytes:
    entries = b""
    for i, name in enumerate(names):
        name_b = name.encode().ljust(32, b"\x00")
        unit_b = b"".ljust(16, b"\x00")
        entries += CHANNEL_ENTRY_FMT.pack(i, name_b, unit_b, 0, 0.0, 1000.0)
    return entries


def test_parse_channel_list():
    data = _make_channel_list(["speed", "rpm", "throttle"])
    ch_map = _parse_channel_list(data)
    assert ch_map == {0: "speed", 1: "rpm", 2: "throttle"}


def test_parse_channel_list_empty():
    assert _parse_channel_list(b"") == {}


# ── StreamingClient unit tests ────────────────────────────────────────────────


class _FakeManager:
    """Minimal ConnectionManager substitute that records broadcasts."""

    def __init__(self):
        self.broadcasts: list[dict] = []

    async def broadcast(self, channel: str, data: dict) -> None:
        self.broadcasts.append(data)


def test_streaming_client_initial_state():
    manager = _FakeManager()
    client = StreamingClient(manager)

    assert client.state == STATE_IDLE
    assert not client.connected
    assert client.channel_names == []
    stats = client.stats
    assert stats["state"] == STATE_IDLE
    assert stats["rx_frames"] == 0
    assert stats["lost_packets"] == 0
    assert stats["channel_count"] == 0


def test_streaming_client_on_udp_packet_valid():
    """Valid UDP packet updates rx_frames and populates buffer."""
    manager = _FakeManager()
    client = StreamingClient(manager)
    client._channel_map = {0: "speed", 1: "rpm"}

    frame = _make_udp_frame(seq=0, ts=1.0, channels={0: 100.0, 1: 5000.0})
    client._last_seq = -1
    client._on_udp_packet(frame)

    assert client._rx_frames == 1
    assert client._lost_packets == 0
    assert len(client._buffer) == 1
    recv_ts, frame_ts, channels = client._buffer[0]
    assert abs(frame_ts - 1.0) < 1e-9
    assert recv_ts > 0  # local monotonic time
    assert channels["speed"] == pytest.approx(100.0)
    assert channels["rpm"] == pytest.approx(5000.0)


def test_streaming_client_on_udp_packet_loss():
    """Gap in sequence numbers increments lost_packets."""
    manager = _FakeManager()
    client = StreamingClient(manager)

    f0 = _make_udp_frame(seq=0, ts=0.0, channels={0: 1.0})
    client._last_seq = -1
    client._on_udp_packet(f0)
    assert client._lost_packets == 0

    # Skip seq 1 and 2; receive seq=3 → 2 packets lost
    f3 = _make_udp_frame(seq=3, ts=0.1, channels={0: 2.0})
    client._on_udp_packet(f3)
    assert client._lost_packets == 2


def test_streaming_client_on_udp_packet_bad_magic():
    """Packets with wrong magic are silently dropped."""
    manager = _FakeManager()
    client = StreamingClient(manager)

    frame = _make_udp_frame(seq=0, ts=0.0, channels={0: 1.0})
    bad = b"XXXX" + frame[4:]
    client._on_udp_packet(bad)
    assert client._rx_frames == 0


def test_streaming_client_on_udp_packet_too_short():
    """Packets shorter than the header are silently dropped."""
    manager = _FakeManager()
    client = StreamingClient(manager)

    client._on_udp_packet(b"\x00" * 5)
    assert client._rx_frames == 0


def test_streaming_client_unknown_channel_id():
    """Unknown channel IDs get a fallback name."""
    manager = _FakeManager()
    client = StreamingClient(manager)
    client._channel_map = {0: "speed"}  # only ch0 is known

    frame = _make_udp_frame(seq=0, ts=0.0, channels={0: 100.0, 99: 42.0})
    client._last_seq = -1
    client._on_udp_packet(frame)

    _, _frame_ts, channels = client._buffer[0]
    assert channels["speed"] == pytest.approx(100.0)
    assert channels["ch99"] == pytest.approx(42.0)


@pytest.mark.anyio
async def test_streaming_client_stop_without_start():
    """stop() on an unstarted client must not raise."""
    manager = _FakeManager()
    client = StreamingClient(manager)
    await client.stop()
    assert client.state == STATE_IDLE


@pytest.mark.anyio
async def test_streaming_client_buffer_flusher():
    """Jitter buffer flushes old frames to broadcast."""
    import asyncio

    manager = _FakeManager()
    client = StreamingClient(manager)

    # Pre-populate with a frame whose receive time is > BUFFER_MS ago.
    old_ts = time.monotonic() - 0.2
    client._buffer.append((old_ts, 1.0, {"speed": 50.0}))

    task = asyncio.create_task(client._buffer_flusher())
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(manager.broadcasts) >= 1
    assert manager.broadcasts[0]["channels"]["speed"] == pytest.approx(50.0)
    assert manager.broadcasts[0]["type"] == "telemetry"
