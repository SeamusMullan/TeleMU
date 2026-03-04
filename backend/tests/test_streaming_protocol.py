"""Tests for the streaming protocol encode/decode layer and loopback streaming.

These tests exercise:
- Discovery packet round-trips
- Control message encoding/decoding (HELLO, WELCOME, SUBSCRIBE, PING, DISCONNECT, …)
- Telemetry frame encoding/decoding with and without LZ4 compression
- Packet-size constraints (MTU guard)
- Loopback end-to-end: TelemetryStreamer ↔ StreamClient over 127.0.0.1
- Sequence number monotonicity
- Channel ID canonical mapping consistency
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

from telemu.streaming.protocol import (
    CHANNEL_ID,
    CHANNEL_NAME,
    MAX_UDP_PAYLOAD,
    STREAM_MAGIC,
    ChannelInfo,
    DisconnectReason,
    MsgType,
    TelemetryFrame,
    decode_discovery,
    decode_hello,
    decode_ping_pong,
    decode_session_update,
    decode_subscribe,
    decode_subscribed,
    decode_telemetry_frame,
    decode_welcome,
    encode_disconnect,
    encode_discovery,
    encode_hello,
    encode_ping,
    encode_pong,
    encode_session_update,
    encode_subscribe,
    encode_subscribed,
    encode_telemetry_frame,
    encode_welcome,
)
from telemu.streaming.streamer import TelemetryStreamer
from telemu.streaming.client import StreamClient


# ── Helpers ───────────────────────────────────────────────────────────────────


def _free_port() -> int:
    """Return a free TCP/UDP port on loopback."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_SAMPLE_CHANNELS = [
    ChannelInfo(channel_id=0, name="speed", unit="km/h", type_tag=0, min_val=0, max_val=400),
    ChannelInfo(channel_id=1, name="rpm", unit="rpm", type_tag=0, min_val=0, max_val=12000),
    ChannelInfo(channel_id=2, name="throttle", unit="%", type_tag=0, min_val=0, max_val=100),
]


# ── Discovery ─────────────────────────────────────────────────────────────────


class TestDiscovery:
    def test_roundtrip(self):
        pkt = encode_discovery(
            driver_name="Alice",
            track_name="Spa",
            vehicle_name="GT3",
            session_type=1,
            tcp_port=9101,
            udp_port=9100,
            session_id=42,
        )
        info = decode_discovery(pkt)
        assert info["driver_name"] == "Alice"
        assert info["track_name"] == "Spa"
        assert info["vehicle_name"] == "GT3"
        assert info["session_type"] == 1
        assert info["tcp_port"] == 9101
        assert info["udp_port"] == 9100
        assert info["session_id"] == 42
        assert info["version"] == 2

    def test_magic_mismatch_raises(self):
        pkt = encode_discovery(driver_name="Bob", track_name="", vehicle_name="")
        bad = b"BAD\x00" + pkt[4:]
        with pytest.raises(ValueError, match="magic"):
            decode_discovery(bad)

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            decode_discovery(b"\x00" * 10)

    def test_wrong_msg_type_raises(self):
        pkt = bytearray(encode_discovery(driver_name="X", track_name="", vehicle_name=""))
        pkt[6] = 0xFF  # corrupt msg_type
        with pytest.raises(ValueError):
            decode_discovery(bytes(pkt))

    def test_long_name_truncated(self):
        pkt = encode_discovery(
            driver_name="A" * 100,  # wider than 32-byte field
            track_name="",
            vehicle_name="",
        )
        info = decode_discovery(pkt)
        assert len(info["driver_name"]) == 32

    def test_magic_bytes(self):
        pkt = encode_discovery(driver_name="", track_name="", vehicle_name="")
        assert pkt[:4] == STREAM_MAGIC


# ── Control messages ──────────────────────────────────────────────────────────


class TestHello:
    def test_roundtrip(self):
        raw = encode_hello("Race Engineer 1")
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.HELLO
        info = decode_hello(payload)
        assert info["client_name"] == "Race Engineer 1"
        assert info["protocol_version"] == 2

    def test_name_truncated_at_32(self):
        raw = encode_hello("E" * 50)
        _, payload = _decode(raw)
        info = decode_hello(payload)
        assert len(info["client_name"]) == 32


class TestWelcome:
    def test_roundtrip_no_channels(self):
        raw = encode_welcome(session_id=99, channels=[])
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.WELCOME
        info = decode_welcome(payload)
        assert info["session_id"] == 99
        assert info["channels"] == []

    def test_roundtrip_with_channels(self):
        raw = encode_welcome(session_id=7, channels=_SAMPLE_CHANNELS)
        _, payload = _decode(raw)
        info = decode_welcome(payload)
        assert info["session_id"] == 7
        assert len(info["channels"]) == 3
        ch = info["channels"][0]
        assert ch.name == "speed"
        assert ch.unit == "km/h"
        assert ch.channel_id == 0
        assert ch.min_val == 0.0
        assert ch.max_val == 400.0


class TestSubscribe:
    def test_roundtrip_subscribe(self):
        raw = encode_subscribe([0, 1, 2], udp_port=9100)
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.SUBSCRIBE
        info = decode_subscribe(payload)
        assert set(info["channel_ids"]) == {0, 1, 2}
        assert info["udp_port"] == 9100

    def test_subscribe_default_udp_port(self):
        from telemu.streaming.protocol import TELEMETRY_PORT
        raw = encode_subscribe([0, 1])
        _, payload = _decode(raw)
        info = decode_subscribe(payload)
        assert info["udp_port"] == TELEMETRY_PORT

    def test_roundtrip_subscribed(self):
        raw = encode_subscribed([5, 10])
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.SUBSCRIBED
        info = decode_subscribed(payload)
        assert set(info["channel_ids"]) == {5, 10}

    def test_empty_subscribe(self):
        raw = encode_subscribe([])
        _, payload = _decode(raw)
        info = decode_subscribe(payload)
        assert info["channel_ids"] == []


class TestSessionUpdate:
    def test_roundtrip(self):
        raw = encode_session_update("Silverstone", "LMP2", session_type=2)
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.SESSION_UPDATE
        info = decode_session_update(payload)
        assert info["track"] == "Silverstone"
        assert info["vehicle"] == "LMP2"
        assert info["session_type"] == 2


class TestPingPong:
    def test_ping_roundtrip(self):
        ts = 1234.5678
        raw = encode_ping(ts)
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.PING
        assert decode_ping_pong(payload) == pytest.approx(ts)

    def test_pong_roundtrip(self):
        ts = 9999.0
        raw = encode_pong(ts)
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.PONG
        assert decode_ping_pong(payload) == pytest.approx(ts)


class TestDisconnect:
    def test_roundtrip(self):
        raw = encode_disconnect(DisconnectReason.SESSION_END)
        msg_type, payload = _decode(raw)
        assert msg_type == MsgType.DISCONNECT
        assert payload[0] == DisconnectReason.SESSION_END


# ── Telemetry frames ──────────────────────────────────────────────────────────


class TestTelemetryFrame:
    def _sample_channels(self) -> dict[int, float]:
        return {0: 180.0, 1: 6000.0, 2: 85.5, 3: 0.0, 4: 4.0}

    def test_roundtrip_compressed(self):
        ch = self._sample_channels()
        pkt = encode_telemetry_frame(
            session_id=1, sequence=5, timestamp=10.0, channels=ch, compress=True
        )
        frame = decode_telemetry_frame(pkt)
        assert frame.session_id == 1
        assert frame.sequence == 5
        assert frame.timestamp == pytest.approx(10.0)
        assert frame.channels == pytest.approx(ch)

    def test_roundtrip_uncompressed(self):
        ch = self._sample_channels()
        pkt = encode_telemetry_frame(
            session_id=2, sequence=0, timestamp=0.016, channels=ch, compress=False
        )
        frame = decode_telemetry_frame(pkt)
        assert frame.channels == pytest.approx(ch)

    def test_empty_channels(self):
        pkt = encode_telemetry_frame(
            session_id=0, sequence=0, timestamp=0.0, channels={}, compress=True
        )
        frame = decode_telemetry_frame(pkt)
        assert frame.channels == {}

    def test_packet_under_mtu(self):
        # 22 channels should stay well under 1400 bytes
        ch = {i: float(i * 10) for i in range(22)}
        pkt = encode_telemetry_frame(
            session_id=0, sequence=0, timestamp=0.0, channels=ch, compress=True
        )
        assert len(pkt) <= MAX_UDP_PAYLOAD

    def test_too_large_raises(self):
        # Build enough channels to exceed MTU (140+ channels * 10 bytes each = 1400 bytes raw,
        # which LZ4 may not compress enough)
        ch = {i: float(i) for i in range(200)}
        with pytest.raises(ValueError, match="too large"):
            encode_telemetry_frame(
                session_id=0, sequence=0, timestamp=0.0, channels=ch, compress=False
            )

    def test_invalid_magic_raises(self):
        pkt = encode_telemetry_frame(
            session_id=0, sequence=0, timestamp=0.0, channels={0: 1.0}, compress=False
        )
        bad = b"XXXX" + pkt[4:]
        with pytest.raises(ValueError, match="magic"):
            decode_telemetry_frame(bad)

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            decode_telemetry_frame(b"\x00" * 5)

    def test_sequence_wraps(self):
        """Sequence number wraps at 2^32."""
        pkt = encode_telemetry_frame(
            session_id=0, sequence=0xFFFFFFFF, timestamp=0.0, channels={0: 1.0}
        )
        frame = decode_telemetry_frame(pkt)
        assert frame.sequence == 0xFFFFFFFF


# ── Canonical channel map ─────────────────────────────────────────────────────


class TestChannelMap:
    def test_reverse_mapping_consistent(self):
        for name, ch_id in CHANNEL_ID.items():
            assert CHANNEL_NAME[ch_id] == name

    def test_no_duplicate_ids(self):
        ids = list(CHANNEL_ID.values())
        assert len(ids) == len(set(ids)), "Duplicate channel IDs in CHANNEL_ID"

    def test_known_channels_present(self):
        for name in ("speed", "rpm", "throttle", "brake", "gear", "steering", "fuel"):
            assert name in CHANNEL_ID


# ── Loopback integration test ─────────────────────────────────────────────────


class TestLoopbackStreaming:
    """End-to-end loopback test using TelemetryStreamer and StreamClient."""

    def test_handshake_and_frame_delivery(self):
        """One frame sent by the streamer should be received by the client."""
        ctrl_port = _free_port()
        telem_port = _free_port()
        disc_port = _free_port()
        local_udp = _free_port()

        channels = _SAMPLE_CHANNELS[:]
        streamer = TelemetryStreamer(
            session_id=123,
            channels=channels,
            driver_name="TestDriver",
            track_name="Monza",
            vehicle_name="GTE",
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )
        streamer.start()

        received: list[TelemetryFrame] = []
        connected_event = threading.Event()

        client = StreamClient(
            client_name="TestEngineer",
            on_frame=received.append,
            on_connected=lambda _: connected_event.set(),
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )

        try:
            client.connect("127.0.0.1", ctrl_port, local_udp_port=local_udp)
            assert connected_event.wait(timeout=3.0), "Client did not connect in time"

            # Push a frame
            frame_channels = {0: 200.0, 1: 7500.0, 2: 100.0}
            streamer.push_frame(timestamp=1.0, channels=frame_channels, compress=True)

            # Wait for the frame to arrive
            deadline = time.monotonic() + 3.0
            while not received and time.monotonic() < deadline:
                time.sleep(0.05)

            assert received, "No telemetry frame received"
            f = received[0]
            assert f.session_id == 123
            assert f.timestamp == pytest.approx(1.0)
            assert f.channels[0] == pytest.approx(200.0)
            assert f.channels[1] == pytest.approx(7500.0)

        finally:
            client.disconnect()
            streamer.stop()

    def test_multi_client(self):
        """Two clients can connect simultaneously and both receive frames."""
        ctrl_port = _free_port()
        telem_port = _free_port()
        disc_port = _free_port()

        streamer = TelemetryStreamer(
            session_id=1,
            channels=_SAMPLE_CHANNELS[:],
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )
        streamer.start()

        frames_a: list[TelemetryFrame] = []
        frames_b: list[TelemetryFrame] = []
        ev_a, ev_b = threading.Event(), threading.Event()

        client_a = StreamClient(
            client_name="EngA",
            on_frame=frames_a.append,
            on_connected=lambda _: ev_a.set(),
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )
        client_b = StreamClient(
            client_name="EngB",
            on_frame=frames_b.append,
            on_connected=lambda _: ev_b.set(),
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )

        try:
            client_a.connect("127.0.0.1", ctrl_port, local_udp_port=_free_port())
            client_b.connect("127.0.0.1", ctrl_port, local_udp_port=_free_port())
            assert ev_a.wait(3.0) and ev_b.wait(3.0), "Clients did not connect"
            assert len(streamer.connected_clients()) == 2

            streamer.push_frame(timestamp=2.0, channels={0: 150.0, 1: 5000.0, 2: 50.0})

            deadline = time.monotonic() + 3.0
            while (not frames_a or not frames_b) and time.monotonic() < deadline:
                time.sleep(0.05)

            assert frames_a, "Client A received no frames"
            assert frames_b, "Client B received no frames"

        finally:
            client_a.disconnect()
            client_b.disconnect()
            streamer.stop()

    def test_sequence_monotonic(self):
        """Sequence numbers should increase with each push_frame call."""
        ctrl_port = _free_port()
        telem_port = _free_port()
        disc_port = _free_port()
        local_udp = _free_port()

        streamer = TelemetryStreamer(
            session_id=5,
            channels=_SAMPLE_CHANNELS[:],
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )
        streamer.start()

        received: list[TelemetryFrame] = []
        ev = threading.Event()

        client = StreamClient(
            client_name="SeqTest",
            on_frame=received.append,
            on_connected=lambda _: ev.set(),
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )

        try:
            client.connect("127.0.0.1", ctrl_port, local_udp_port=local_udp)
            assert ev.wait(3.0)

            n = 5
            for i in range(n):
                streamer.push_frame(timestamp=float(i) * 0.016, channels={0: float(i)})
                time.sleep(0.01)

            deadline = time.monotonic() + 3.0
            while len(received) < n and time.monotonic() < deadline:
                time.sleep(0.05)

            # UDP may reorder or drop, but sequences must be non-decreasing
            seqs = [f.sequence for f in received]
            assert seqs == sorted(seqs), f"Sequences out of order: {seqs}"
            # All sequences should be unique
            assert len(seqs) == len(set(seqs)), f"Duplicate sequences: {seqs}"

        finally:
            client.disconnect()
            streamer.stop()

    def test_session_update_delivered(self):
        """SESSION_UPDATE sent by streamer reaches the client callback."""
        ctrl_port = _free_port()
        telem_port = _free_port()
        disc_port = _free_port()
        local_udp = _free_port()

        streamer = TelemetryStreamer(
            session_id=99,
            channels=_SAMPLE_CHANNELS[:],
            track_name="Interlagos",
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )
        streamer.start()

        updates: list[dict] = []
        ev = threading.Event()

        client = StreamClient(
            client_name="UpdateTest",
            on_connected=lambda _: ev.set(),
            on_session_update=updates.append,
            discovery_port=disc_port,
            control_port=ctrl_port,
            telemetry_port=telem_port,
        )

        try:
            client.connect("127.0.0.1", ctrl_port, local_udp_port=local_udp)
            assert ev.wait(3.0)

            streamer.update_session("Le Mans", "Hypercar", session_type=3)

            deadline = time.monotonic() + 3.0
            while not updates and time.monotonic() < deadline:
                time.sleep(0.05)

            assert updates, "No session update received"
            assert updates[0]["track"] == "Le Mans"
            assert updates[0]["vehicle"] == "Hypercar"
            assert updates[0]["session_type"] == 3

        finally:
            client.disconnect()
            streamer.stop()


# ── Helper ────────────────────────────────────────────────────────────────────


def _decode(raw: bytes) -> tuple[MsgType, bytes]:
    """Decode a framed control message and return (msg_type, payload)."""
    from telemu.streaming.protocol import _decode_ctrl_header
    return _decode_ctrl_header(raw)
