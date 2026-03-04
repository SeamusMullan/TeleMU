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
