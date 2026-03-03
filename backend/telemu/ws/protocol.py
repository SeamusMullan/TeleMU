"""WebSocket message type registry and channel definitions."""

from __future__ import annotations

# Server → Client message types
TELEMETRY = "telemetry"
SCORING = "scoring"
STATUS = "status"
ENGINEER = "engineer"
RECORDING = "recording"

# Client → Server message types
SUBSCRIBE = "subscribe"
RECORD = "record"
PLAYBACK = "playback"
THROTTLE = "throttle"

# All subscribable channels
CHANNELS = frozenset({TELEMETRY, SCORING, STATUS, ENGINEER, RECORDING})

# Default subscription for new clients
DEFAULT_CHANNELS = frozenset({TELEMETRY, SCORING, STATUS})
