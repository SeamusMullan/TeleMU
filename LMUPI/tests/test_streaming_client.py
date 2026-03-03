"""Tests for the telemetry streaming client protocol logic."""

from __future__ import annotations

import json
import struct
import sys
import time
import unittest
from unittest import mock

# Provide a lightweight PySide6 stub so the streaming_client module can be
# imported without the real (heavy) PySide6 dependency.
_pyside6_stub = mock.MagicMock()
sys.modules.setdefault("PySide6", _pyside6_stub)
sys.modules.setdefault("PySide6.QtCore", _pyside6_stub)

from lmupi.streaming_client import (  # noqa: E402
    ChannelSpec,
    JitterBuffer,
    TelemetryFrame,
    build_handshake_request,
    parse_channel_map,
    parse_udp_frame,
    _HANDSHAKE_MAGIC,
    _HANDSHAKE_VERSION,
)


class TestHandshake(unittest.TestCase):
    """Verify the TCP handshake request/response encoding."""

    def test_build_handshake_request(self) -> None:
        req = build_handshake_request()
        self.assertEqual(req[:4], _HANDSHAKE_MAGIC)
        self.assertEqual(req[4], _HANDSHAKE_VERSION)
        self.assertEqual(len(req), 5)

    def test_parse_channel_map_basic(self) -> None:
        payload = {
            "udp_port": 9200,
            "channels": [
                {"name": "Speed", "unit": "km/h", "min": 0, "max": 340},
                {"name": "RPM", "unit": "rpm", "min": 0, "max": 9000, "warn_high": 8500},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        channels, udp_port = parse_channel_map(data)

        self.assertEqual(udp_port, 9200)
        self.assertEqual(len(channels), 2)
        self.assertEqual(channels[0].name, "Speed")
        self.assertEqual(channels[0].unit, "km/h")
        self.assertEqual(channels[0].min_val, 0)
        self.assertEqual(channels[0].max_val, 340)
        self.assertIsNone(channels[0].warn_high)
        self.assertEqual(channels[1].name, "RPM")
        self.assertEqual(channels[1].warn_high, 8500)

    def test_parse_channel_map_defaults(self) -> None:
        payload = {
            "udp_port": 5000,
            "channels": [{"name": "Throttle"}],
        }
        data = json.dumps(payload).encode("utf-8")
        channels, udp_port = parse_channel_map(data)

        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0].unit, "")
        self.assertEqual(channels[0].min_val, 0.0)
        self.assertEqual(channels[0].max_val, 100.0)
        self.assertIsNone(channels[0].warn_low)
        self.assertEqual(channels[0].display, "gauge")

    def test_parse_channel_map_display_spark(self) -> None:
        payload = {
            "udp_port": 5000,
            "channels": [{"name": "Tyre FL", "display": "spark"}],
        }
        data = json.dumps(payload).encode("utf-8")
        channels, _ = parse_channel_map(data)
        self.assertEqual(channels[0].display, "spark")


class TestUDPFrameParsing(unittest.TestCase):
    """Verify binary UDP frame decoding."""

    def _make_frame(self, seq: int, pairs: list[tuple[int, float]]) -> bytes:
        buf = struct.pack("!I", seq)
        for idx, val in pairs:
            buf += struct.pack("!Hf", idx, val)
        return buf

    def test_parse_valid_frame(self) -> None:
        raw = self._make_frame(42, [(0, 120.5), (1, 7200.0)])
        frame = parse_udp_frame(raw)

        self.assertIsNotNone(frame)
        self.assertEqual(frame.seq, 42)
        self.assertEqual(len(frame.pairs), 2)
        self.assertEqual(frame.pairs[0][0], 0)
        self.assertAlmostEqual(frame.pairs[0][1], 120.5, places=1)
        self.assertEqual(frame.pairs[1][0], 1)
        self.assertAlmostEqual(frame.pairs[1][1], 7200.0, places=1)

    def test_parse_empty_body(self) -> None:
        raw = struct.pack("!I", 1)  # header only, no pairs
        frame = parse_udp_frame(raw)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.seq, 1)
        self.assertEqual(len(frame.pairs), 0)

    def test_parse_too_short(self) -> None:
        self.assertIsNone(parse_udp_frame(b""))
        self.assertIsNone(parse_udp_frame(b"\x00\x01\x02"))

    def test_parse_malformed_body(self) -> None:
        raw = struct.pack("!I", 5) + b"\x00\x01"  # body not multiple of 6
        self.assertIsNone(parse_udp_frame(raw))

    def test_large_sequence_number(self) -> None:
        raw = self._make_frame(2**32 - 1, [(0, 1.0)])
        frame = parse_udp_frame(raw)
        self.assertEqual(frame.seq, 2**32 - 1)


class TestJitterBuffer(unittest.TestCase):
    """Verify jitter buffer ordering, dedup, and timed release."""

    def _frame(self, seq: int, ts: float | None = None) -> TelemetryFrame:
        return TelemetryFrame(
            seq=seq,
            timestamp=ts if ts is not None else time.monotonic(),
            pairs=[(0, float(seq))],
        )

    def test_in_order_release(self) -> None:
        buf = JitterBuffer(buffer_ms=0)  # no delay — release immediately
        buf.put(self._frame(1))
        buf.put(self._frame(2))
        buf.put(self._frame(3))

        frames = buf.flush()
        seqs = [f.seq for f in frames]
        self.assertEqual(seqs, [1, 2, 3])

    def test_out_of_order_sorted(self) -> None:
        buf = JitterBuffer(buffer_ms=0)
        buf.put(self._frame(3))
        buf.put(self._frame(1))
        buf.put(self._frame(2))

        frames = buf.flush()
        seqs = [f.seq for f in frames]
        self.assertEqual(seqs, [1, 2, 3])

    def test_duplicate_dropped(self) -> None:
        buf = JitterBuffer(buffer_ms=0)
        buf.put(self._frame(1))
        buf.flush()
        buf.put(self._frame(1))  # duplicate — should be dropped on put

        frames = buf.flush()
        self.assertEqual(len(frames), 0)

    def test_old_frame_dropped(self) -> None:
        buf = JitterBuffer(buffer_ms=0)
        buf.put(self._frame(5))
        buf.flush()
        buf.put(self._frame(3))  # older than last released

        frames = buf.flush()
        self.assertEqual(len(frames), 0)

    def test_gap_handling(self) -> None:
        """Packet loss (missing seq 2) — should release 1 and 3, skipping gap."""
        buf = JitterBuffer(buffer_ms=0)
        buf.put(self._frame(1))
        buf.put(self._frame(3))  # seq 2 lost

        frames = buf.flush()
        seqs = [f.seq for f in frames]
        self.assertEqual(seqs, [1, 3])

    def test_timed_buffer(self) -> None:
        """Frames should not be released until buffer time has elapsed."""
        buf = JitterBuffer(buffer_ms=200)
        now = time.monotonic()
        buf.put(self._frame(1, ts=now))

        # Should not release yet
        frames = buf.flush()
        self.assertEqual(len(frames), 0)

    def test_timed_buffer_release_after_delay(self) -> None:
        """Frames should be released after buffer time passes."""
        buf = JitterBuffer(buffer_ms=50)
        past = time.monotonic() - 0.1  # 100ms ago
        buf.put(self._frame(1, ts=past))

        frames = buf.flush()
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].seq, 1)

    def test_reset(self) -> None:
        buf = JitterBuffer(buffer_ms=0)
        buf.put(self._frame(5))
        buf.flush()
        buf.reset()

        # After reset, seq 1 should be accepted again
        buf.put(self._frame(1))
        frames = buf.flush()
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].seq, 1)


if __name__ == "__main__":
    unittest.main()
