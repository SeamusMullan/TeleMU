"""Tests for the telemetry streaming protocol serialization."""

from __future__ import annotations

import time
import unittest

from lmupi.streaming.protocol import (
    DEFAULT_PORT,
    PROTOCOL_VERSION,
    MsgType,
    pack_control_message,
    pack_telemetry_frame,
    unpack_control_message,
    unpack_telemetry_frame,
)


class TestTelemetryFrame(unittest.TestCase):
    """Round-trip tests for UDP telemetry frame packing/unpacking."""

    def test_round_trip_basic(self) -> None:
        channels = {"Speed": 280.5, "RPM": 7200.0, "Throttle": 85.3}
        ts = time.time()
        packet = pack_telemetry_frame(42, channels, timestamp=ts)

        seq, rts, rch = unpack_telemetry_frame(packet)
        self.assertEqual(seq, 42)
        self.assertAlmostEqual(rts, ts, places=3)
        self.assertEqual(set(rch.keys()), set(channels.keys()))
        for k in channels:
            self.assertAlmostEqual(rch[k], channels[k], places=6)

    def test_round_trip_single_channel(self) -> None:
        channels = {"Fuel": 55.123}
        packet = pack_telemetry_frame(1, channels)
        seq, _, rch = unpack_telemetry_frame(packet)
        self.assertEqual(seq, 1)
        self.assertAlmostEqual(rch["Fuel"], 55.123, places=6)

    def test_round_trip_many_channels(self) -> None:
        channels = {f"ch_{i}": float(i) * 1.1 for i in range(50)}
        packet = pack_telemetry_frame(999, channels)

        seq, _, rch = unpack_telemetry_frame(packet)
        self.assertEqual(seq, 999)
        self.assertEqual(len(rch), 50)
        for k, v in channels.items():
            self.assertAlmostEqual(rch[k], v, places=6)

    def test_packet_under_1400_bytes(self) -> None:
        """Typical telemetry should fit in a single UDP packet."""
        channels = {
            "Speed": 280.5, "RPM": 7200.0, "Throttle": 85.3,
            "Brake": 0.0, "Gear": 6.0, "Steering": -12.5,
            "Tyre FL": 95.2, "Tyre FR": 96.1, "Tyre RL": 93.4, "Tyre RR": 94.0,
            "Fuel": 55.0, "Brake Temp": 420.0,
        }
        packet = pack_telemetry_frame(1, channels)
        self.assertLess(len(packet), 1400)

    def test_sequence_wraps(self) -> None:
        """Sequence numbers should wrap at 32-bit."""
        packet = pack_telemetry_frame(0xFFFFFFFF, {"x": 1.0})
        seq, _, _ = unpack_telemetry_frame(packet)
        self.assertEqual(seq, 0xFFFFFFFF)

    def test_empty_channels_raises(self) -> None:
        """Empty channel dict still produces a valid frame."""
        packet = pack_telemetry_frame(0, {})
        seq, _, rch = unpack_telemetry_frame(packet)
        self.assertEqual(seq, 0)
        self.assertEqual(rch, {})

    def test_negative_values(self) -> None:
        channels = {"Steering": -350.5, "LateralG": -2.1}
        packet = pack_telemetry_frame(7, channels)
        _, _, rch = unpack_telemetry_frame(packet)
        self.assertAlmostEqual(rch["Steering"], -350.5, places=6)
        self.assertAlmostEqual(rch["LateralG"], -2.1, places=6)

    def test_truncated_packet_raises(self) -> None:
        packet = pack_telemetry_frame(1, {"Speed": 100.0})
        with self.assertRaises(ValueError):
            unpack_telemetry_frame(packet[:5])

    def test_wrong_version_raises(self) -> None:
        packet = bytearray(pack_telemetry_frame(1, {"Speed": 100.0}))
        packet[0] = 99  # corrupt version
        with self.assertRaises(ValueError):
            unpack_telemetry_frame(bytes(packet))


class TestControlMessage(unittest.TestCase):
    """Round-trip tests for TCP control message packing/unpacking."""

    def test_handshake_req(self) -> None:
        payload = {"client_name": "Engineer-1"}
        data = pack_control_message(MsgType.HANDSHAKE_REQ, payload)
        msg_type, rpayload = unpack_control_message(data)
        self.assertEqual(msg_type, MsgType.HANDSHAKE_REQ)
        self.assertEqual(rpayload["client_name"], "Engineer-1")

    def test_handshake_ack(self) -> None:
        payload = {"channels": ["Speed", "RPM", "Fuel"], "udp_port": 19741}
        data = pack_control_message(MsgType.HANDSHAKE_ACK, payload)
        msg_type, rpayload = unpack_control_message(data)
        self.assertEqual(msg_type, MsgType.HANDSHAKE_ACK)
        self.assertEqual(rpayload["channels"], ["Speed", "RPM", "Fuel"])
        self.assertEqual(rpayload["udp_port"], 19741)

    def test_heartbeat(self) -> None:
        data = pack_control_message(MsgType.HEARTBEAT)
        msg_type, rpayload = unpack_control_message(data)
        self.assertEqual(msg_type, MsgType.HEARTBEAT)
        self.assertEqual(rpayload, {})

    def test_goodbye(self) -> None:
        data = pack_control_message(MsgType.GOODBYE)
        msg_type, _ = unpack_control_message(data)
        self.assertEqual(msg_type, MsgType.GOODBYE)

    def test_channel_subscription(self) -> None:
        payload = {"channels": ["Speed", "RPM"]}
        data = pack_control_message(MsgType.CHANNEL_SUB, payload)
        msg_type, rpayload = unpack_control_message(data)
        self.assertEqual(msg_type, MsgType.CHANNEL_SUB)
        self.assertEqual(rpayload["channels"], ["Speed", "RPM"])

    def test_truncated_control_raises(self) -> None:
        data = pack_control_message(MsgType.HEARTBEAT)
        with self.assertRaises(ValueError):
            unpack_control_message(data[:3])

    def test_wrong_version_control_raises(self) -> None:
        data = bytearray(pack_control_message(MsgType.HEARTBEAT))
        data[0] = 99
        with self.assertRaises(ValueError):
            unpack_control_message(bytes(data))


class TestConstants(unittest.TestCase):
    def test_default_port(self) -> None:
        self.assertEqual(DEFAULT_PORT, 19740)

    def test_protocol_version(self) -> None:
        self.assertEqual(PROTOCOL_VERSION, 1)


if __name__ == "__main__":
    unittest.main()
