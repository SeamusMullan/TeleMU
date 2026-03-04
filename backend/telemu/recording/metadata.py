"""Session metadata extraction from LMU shared memory data."""

from __future__ import annotations

from datetime import datetime, timezone

from telemu.models import SessionMetadata

# Session type mapping from LMU's mSession field
# 0=testday 1-4=practice 5-8=qual 9=warmup 10-13=race
_SESSION_TYPES: dict[int, str] = {
    0: "Test Day",
    1: "Practice 1",
    2: "Practice 2",
    3: "Practice 3",
    4: "Practice 4",
    5: "Qualifying 1",
    6: "Qualifying 2",
    7: "Qualifying 3",
    8: "Qualifying 4",
    9: "Warmup",
    10: "Race 1",
    11: "Race 2",
    12: "Race 3",
    13: "Race 4",
}


def decode_session_type(session_id: int) -> str:
    """Decode LMU mSession integer to human-readable string."""
    return _SESSION_TYPES.get(session_id, f"Unknown ({session_id})")


def _decode_bytes(value: bytes | str) -> str:
    """Decode a ctypes char array to a clean string."""
    if isinstance(value, bytes):
        return value.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    return str(value)


def extract_metadata(scoring_info, vehicle_scoring, vehicle_telemetry) -> SessionMetadata:
    """Extract session metadata from shared memory structures.

    Parameters
    ----------
    scoring_info : LMUScoringInfo
        Session-level scoring data (track name, session type, etc.).
    vehicle_scoring : LMUVehicleScoring
        Player vehicle scoring data (driver name, car number, etc.).
    vehicle_telemetry : LMUVehicleTelemetry
        Player vehicle telemetry data (vehicle name, etc.).

    Returns
    -------
    SessionMetadata
        Populated metadata model.
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    return SessionMetadata(
        track_name=_decode_bytes(scoring_info.mTrackName),
        car_name=_decode_bytes(vehicle_telemetry.mVehicleName),
        car_class=_decode_bytes(vehicle_scoring.mVehicleClass),
        session_type=decode_session_type(scoring_info.mSession),
        driver_name=_decode_bytes(vehicle_scoring.mDriverName),
        car_number=vehicle_scoring.mID,
        session_start_utc=now_utc,
        recording_start_utc=now_utc,
        recording_end_utc="",
    )
