"""REST endpoints for live recording control."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from telemu.config import settings

router = APIRouter(prefix="/live-recording", tags=["live-recording"])


class StartRecordingRequest(BaseModel):
    """Body for starting a new recording."""

    output_dir: str | None = None
    filename: str | None = None


class RecordingStatusResponse(BaseModel):
    """Current recording state returned by all endpoints."""

    active: bool
    filename: str = ""
    output_path: str = ""
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    data_rate_bps: float = 0.0


def _get_recorder(request: Request):
    recorder = getattr(request.app.state, "live_recorder", None)
    if recorder is None:
        raise HTTPException(status_code=503, detail="Recorder not available")
    return recorder


@router.get("/status", response_model=RecordingStatusResponse)
async def get_status(request: Request) -> RecordingStatusResponse:
    """Return current recording status."""
    recorder = _get_recorder(request)
    return RecordingStatusResponse(**recorder.status())


@router.post("/start", response_model=RecordingStatusResponse)
async def start_recording(
    body: StartRecordingRequest, request: Request
) -> RecordingStatusResponse:
    """Start a new recording session."""
    recorder = _get_recorder(request)
    if recorder.active:
        raise HTTPException(status_code=409, detail="Recording already active")

    output_dir = Path(body.output_dir) if body.output_dir else settings.data_dir

    # Grab current track/car from the telemetry store if available
    reader = getattr(request.app.state, "reader", None)
    track = ""
    car = ""
    if reader is not None:
        # Best-effort: pull from last known channels via any attached state
        last = getattr(request.app.state, "last_metadata", None)
        if last:
            track = last.get("track", "")
            car = last.get("car", "")

    try:
        await recorder.start(
            output_dir=output_dir,
            filename=body.filename or None,
            track=track,
            car=car,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return RecordingStatusResponse(**recorder.status())


@router.post("/stop", response_model=RecordingStatusResponse)
async def stop_recording(request: Request) -> RecordingStatusResponse:
    """Stop the active recording and flush data to disk."""
    recorder = _get_recorder(request)
    if not recorder.active:
        raise HTTPException(status_code=409, detail="No active recording")

    try:
        result = await recorder.stop()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return RecordingStatusResponse(**result)
