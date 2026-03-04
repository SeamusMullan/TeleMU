"""Telemetry streaming subsystem — engineer-side client."""

from telemu.streaming.client import StreamingClient
from telemu.streaming.protocol import (
    DEFAULT_TCP_PORT,
    DEFAULT_UDP_PORT,
    DISCOVERY_PORT,
    MSG_HELLO,
    MSG_WELCOME,
    MSG_PING,
    MSG_PONG,
    PROTOCOL_VERSION,
)

__all__ = [
    "StreamingClient",
    "DEFAULT_TCP_PORT",
    "DEFAULT_UDP_PORT",
    "DISCOVERY_PORT",
    "MSG_HELLO",
    "MSG_WELCOME",
    "MSG_PING",
    "MSG_PONG",
    "PROTOCOL_VERSION",
]
"""Streaming subsystem — TelemetryStreamer (driver side)."""

from telemu.streaming.server import TelemetryStreamer

__all__ = ["TelemetryStreamer"]
"""TeleMU LAN streaming subsystem.

Exports
-------
TelemetryStreamer
    Driver-side server: broadcasts discovery, accepts TCP control connections,
    and sends LZ4-compressed UDP telemetry frames to each subscribed engineer.
StreamClient
    Engineer-side client: discovers drivers via UDP broadcast, completes the
    TCP handshake, and receives UDP telemetry frames.
protocol
    Wire-format constants and packet encode/decode functions.
"""

from .client import StreamClient
from .streamer import TelemetryStreamer

__all__ = ["TelemetryStreamer", "StreamClient"]
