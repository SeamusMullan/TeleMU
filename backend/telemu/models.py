"""Pydantic models for API and WebSocket payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── WebSocket messages (server → client) ──────────────────────────────────────


class TelemetryMessage(BaseModel):
    type: str = "telemetry"
    ts: float
    channels: dict[str, float]


class ScoringVehicle(BaseModel):
    id: int
    driver: str
    vehicle: str
    place: int
    laps: int
    last_lap: float
    best_lap: float
    sector: int
    in_pits: bool
    flag: int


class ScoringSession(BaseModel):
    track: str
    session_type: str
    num_vehicles: int
    game_phase: int


class ScoringMessage(BaseModel):
    type: str = "scoring"
    ts: float
    session: ScoringSession
    player: ScoringVehicle
    vehicles: list[ScoringVehicle]


class StatusMessage(BaseModel):
    type: str = "status"
    drs: bool = False
    pit: bool = False
    flag: int = 0
    tc: bool = False
    abs: bool = False


class EngineerMessage(BaseModel):
    type: str = "engineer"
    tool: str
    data: dict[str, Any]


class RecordingStatus(BaseModel):
    type: str = "recording"
    status: str  # "idle" | "recording" | "playing"
    file: str = ""
    frames: int = 0


# ── WebSocket messages (client → server) ──────────────────────────────────────


class SubscribeRequest(BaseModel):
    type: str = "subscribe"
    channels: list[str]


class RecordRequest(BaseModel):
    type: str = "record"
    action: str  # "start" | "stop"


class PlaybackRequest(BaseModel):
    type: str = "playback"
    action: str  # "play" | "pause" | "seek"
    file: str = ""
    ts: float = 0.0


class ThrottleRequest(BaseModel):
    type: str = "throttle"
    max_fps: int = 60


# ── REST API models ───────────────────────────────────────────────────────────


class TableInfo(BaseModel):
    name: str
    row_count: int


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool


class ColumnStats(BaseModel):
    column: str
    type: str
    nulls: int
    distinct: int
    min: float | str | None = None
    max: float | str | None = None
    avg: float | None = None


class QueryRequest(BaseModel):
    sql: str


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    elapsed_ms: float


class SessionInfo(BaseModel):
    filename: str
    path: str
    size_bytes: int
    tables: list[str] = []


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    lmu_connected: bool = False
    active_clients: int = 0


class StreamingStatus(BaseModel):
    running: bool = False
    clients_connected: int = 0
    data_rate_bps: float = 0.0
    host: str = ""
    discovery_port: int = 9099
    telemetry_port: int = 9100
    control_port: int = 9101


# ── Session metadata ─────────────────────────────────────────────────────────


class SessionMetadata(BaseModel):
    """Metadata captured and embedded into .tmu recording files."""

    # Extracted from shared memory
    track_name: str = ""
    car_name: str = ""
    car_class: str = ""
    session_type: str = ""  # human-readable: "Practice", "Qualifying", "Race", etc.

    # Auto-detected from scoring data
    driver_name: str = ""
    car_number: int = 0

    # Timestamps
    session_start_utc: str = ""  # ISO 8601 UTC
    recording_start_utc: str = ""  # ISO 8601 UTC
    recording_end_utc: str = ""  # ISO 8601 UTC

    # User-editable fields
    notes: str = Field(default="", description="Free-form user notes")
    session_description: str = Field(default="", description="User session description")
    setup_name: str = Field(default="", description="Setup name used during session")
