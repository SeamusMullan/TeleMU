"""Tests for the telemetry streaming server."""

from __future__ import annotations

import json
import socket
import time
import unittest

from lmupi.streaming.protocol import (
    DEFAULT_PORT,
    MsgType,
    TCP_HEADER_SIZE,
    pack_control_message,
    unpack_control_message,
    unpack_telemetry_frame,
)
from lmupi.streaming.server import TelemetryStreamingServer


def _find_free_port() -> int:
    """Find a free TCP port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestServerLifecycle(unittest.TestCase):
    """Start/stop and basic client handshake tests."""

    def test_start_stop(self) -> None:
        port = _find_free_port()
        server = TelemetryStreamingServer(port=port, bind_address="127.0.0.1")
        server.start_server()
        # Wait for server to be ready
        time.sleep(0.3)
        self.assertTrue(server.isRunning())
        server.stop_server()
        self.assertFalse(server.isRunning())

    def test_client_handshake(self) -> None:
        port = _find_free_port()
        server = TelemetryStreamingServer(port=port, bind_address="127.0.0.1")
        server.start_server()
        time.sleep(0.3)

        try:
            # Connect a TCP client and perform handshake
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(2.0)
            client.connect(("127.0.0.1", port))

            # Send handshake request
            req = pack_control_message(MsgType.HANDSHAKE_REQ, {
                "client_name": "test-client",
                "udp_port": client.getsockname()[1],
            })
            client.sendall(req)

            # Read handshake ACK
            header = client.recv(TCP_HEADER_SIZE)
            self.assertEqual(len(header), TCP_HEADER_SIZE)
            _, _, payload_len = header[0], header[1], int.from_bytes(header[2:6], "big")
            body = client.recv(payload_len) if payload_len > 0 else b""
            msg_type, payload = unpack_control_message(header + body)

            self.assertEqual(msg_type, MsgType.HANDSHAKE_ACK)
            self.assertIn("channels", payload)
            self.assertIn("udp_port", payload)

            time.sleep(0.3)
            self.assertEqual(server.client_count, 1)

            client.close()
        finally:
            server.stop_server()

    def test_udp_broadcast(self) -> None:
        port = _find_free_port()
        server = TelemetryStreamingServer(port=port, bind_address="127.0.0.1")
        server.start_server()
        time.sleep(0.3)

        try:
            # Set up UDP receive socket
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.settimeout(2.0)
            udp_sock.bind(("127.0.0.1", 0))
            udp_port = udp_sock.getsockname()[1]

            # TCP handshake
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(2.0)
            client.connect(("127.0.0.1", port))

            req = pack_control_message(MsgType.HANDSHAKE_REQ, {
                "client_name": "test-client",
                "udp_port": udp_port,
            })
            client.sendall(req)

            # Read ACK
            header = client.recv(TCP_HEADER_SIZE)
            body_len = int.from_bytes(header[2:6], "big")
            if body_len > 0:
                client.recv(body_len)

            time.sleep(0.3)

            # Broadcast telemetry
            server.broadcast_telemetry({"Speed": 250.0, "RPM": 6800.0})

            # Receive UDP packet
            data, _ = udp_sock.recvfrom(2048)
            seq, ts, channels = unpack_telemetry_frame(data)

            self.assertEqual(seq, 1)
            self.assertAlmostEqual(channels["Speed"], 250.0, places=3)
            self.assertAlmostEqual(channels["RPM"], 6800.0, places=3)

            client.close()
            udp_sock.close()
        finally:
            server.stop_server()

    def test_port_property(self) -> None:
        server = TelemetryStreamingServer(port=19999)
        self.assertEqual(server.port, 19999)
        server.port = 20000
        self.assertEqual(server.port, 20000)

    def test_bind_address_property(self) -> None:
        server = TelemetryStreamingServer(bind_address="127.0.0.1")
        self.assertEqual(server.bind_address, "127.0.0.1")
        server.bind_address = "0.0.0.0"
        self.assertEqual(server.bind_address, "0.0.0.0")


if __name__ == "__main__":
    unittest.main()
