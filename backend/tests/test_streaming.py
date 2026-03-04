"""Tests for the telemetry streaming server (wire format and lifecycle)."""

from __future__ import annotations

import asyncio
import struct
import time

import pytest

from telemu.streaming.server import (
    CHANNEL_DEFS,
    MAGIC,
    MSG_DISCONNECT,
    MSG_DISCOVERY_ANNOUNCE,
    MSG_PONG,
    MSG_SUBSCRIBED,
    MSG_WELCOME,
    PROTOCOL_VERSION,
    REASON_SESSION_END,
    TelemetryStreamer,
    _ALL_CHANNELS_MASK,
    build_disconnect_message,
    build_discovery_packet,
    build_pong_message,
    build_session_update_message,
    build_subscribed_message,
    build_telemetry_frame,
    build_welcome_message,
)


# ── Wire format tests ─────────────────────────────────────────────────────────


def test_discovery_packet_length():
    pkt = build_discovery_packet("Driver", "Track", "Car", 0, 9101, 9100, 42)
    assert len(pkt) == 176


def test_discovery_packet_fields():
    pkt = build_discovery_packet("Alice", "Spa", "LMP1", 1, 9101, 9100, 0xDEADBEEF)
    magic, version, msg_type = struct.unpack_from("<4sHB", pkt, 0)
    assert magic == MAGIC
    assert version == PROTOCOL_VERSION
    assert msg_type == MSG_DISCOVERY_ANNOUNCE
    driver_name = pkt[7:39].rstrip(b"\x00").decode()
    track_name = pkt[39:103].rstrip(b"\x00").decode()
    vehicle_name = pkt[103:167].rstrip(b"\x00").decode()
    assert driver_name == "Alice"
    assert track_name == "Spa"
    assert vehicle_name == "LMP1"
    session_type, tcp_port, udp_port, session_id = struct.unpack_from("<BHHI", pkt, 167)
    assert session_type == 1
    assert tcp_port == 9101
    assert udp_port == 9100
    assert session_id == 0xDEADBEEF


def test_welcome_message_structure():
    msg = build_welcome_message(session_id=1234)
    magic, length, msg_type = struct.unpack_from("<4sHB", msg, 0)
    assert magic == MAGIC
    assert msg_type == MSG_WELCOME
    assert len(msg) == 7 + length


def test_welcome_message_channel_count():
    msg = build_welcome_message(session_id=1)
    # Payload starts at offset 7
    session_id, channel_count = struct.unpack_from("<IH", msg, 7)
    assert channel_count == len(CHANNEL_DEFS)


def test_subscribed_message():
    mask = 0b1111
    msg = build_subscribed_message(mask)
    magic, length, msg_type = struct.unpack_from("<4sHB", msg, 0)
    assert magic == MAGIC
    assert msg_type == MSG_SUBSCRIBED
    mask_bytes = msg[7:]
    recovered = int.from_bytes(mask_bytes, "little") & 0xFFFF
    assert recovered & 0b1111 == mask


def test_disconnect_message():
    msg = build_disconnect_message(REASON_SESSION_END)
    magic, length, msg_type = struct.unpack_from("<4sHB", msg, 0)
    assert magic == MAGIC
    assert msg_type == MSG_DISCONNECT
    reason = struct.unpack_from("<B", msg, 7)[0]
    assert reason == REASON_SESSION_END


def test_pong_message():
    ts = 123.456
    msg = build_pong_message(ts)
    magic, length, msg_type = struct.unpack_from("<4sHB", msg, 0)
    assert magic == MAGIC
    assert msg_type == MSG_PONG
    echo_ts = struct.unpack_from("<d", msg, 7)[0]
    assert abs(echo_ts - ts) < 1e-9


def test_telemetry_frame_structure():
    channels = {name: float(i) for i, (_, name, *_) in enumerate(CHANNEL_DEFS)}
    pkt = build_telemetry_frame(
        session_id=1,
        sequence=10,
        timestamp=0.5,
        channels=channels,
        channel_mask=_ALL_CHANNELS_MASK,
    )
    magic, session_id, sequence, timestamp, channel_count = struct.unpack_from(
        "<4sIIdH", pkt, 0
    )
    assert magic == MAGIC
    assert session_id == 1
    assert sequence == 10
    assert abs(timestamp - 0.5) < 1e-9
    assert channel_count == len(CHANNEL_DEFS)
    # Total size: 22-byte header + 10 bytes per channel
    assert len(pkt) == 22 + channel_count * 10


def test_telemetry_frame_channel_filter():
    channels = {"speed": 100.0, "rpm": 5000.0, "throttle": 80.0}
    mask = 0b111  # channels 0, 1, 2 only
    pkt = build_telemetry_frame(
        session_id=1, sequence=1, timestamp=0.0, channels=channels, channel_mask=mask
    )
    _, _, _, _, channel_count = struct.unpack_from("<4sIIdH", pkt, 0)
    assert channel_count == 3


def test_session_update_message():
    from telemu.streaming.server import MSG_SESSION_UPDATE, build_session_update_message

    msg = build_session_update_message("Spa", "LMP1", 2)
    magic, length, msg_type = struct.unpack_from("<4sHB", msg, 0)
    assert magic == MAGIC
    assert msg_type == MSG_SESSION_UPDATE
    assert length == 129  # 64 + 64 + 1


# ── Lifecycle tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_streamer_start_stop():
    """Streamer starts and stops cleanly."""
    streamer = TelemetryStreamer(
        host="127.0.0.1",
        discovery_port=0,
        telemetry_port=0,
        control_port=19750,
    )
    await streamer.start()
    assert streamer.running
    assert streamer.clients_connected == 0
    await streamer.stop()
    assert not streamer.running


@pytest.mark.asyncio
async def test_streamer_double_start():
    """Calling start() twice is a no-op."""
    streamer = TelemetryStreamer(
        host="127.0.0.1",
        discovery_port=0,
        telemetry_port=0,
        control_port=19751,
    )
    await streamer.start()
    await streamer.start()  # should not raise
    assert streamer.running
    await streamer.stop()


@pytest.mark.asyncio
async def test_streamer_stop_when_not_running():
    """Calling stop() when not running is a no-op."""
    streamer = TelemetryStreamer(host="127.0.0.1")
    await streamer.stop()  # should not raise
    assert not streamer.running


@pytest.mark.asyncio
async def test_on_frame_no_clients():
    """on_frame with no clients does not raise."""
    from telemu.reader import TelemetryFrame

    streamer = TelemetryStreamer(
        host="127.0.0.1",
        discovery_port=0,
        telemetry_port=0,
        control_port=19752,
    )
    await streamer.start()
    frame = TelemetryFrame(ts=time.monotonic(), channels={"speed": 100.0})
    streamer.on_frame(frame)
    await asyncio.sleep(0.05)
    await streamer.stop()
