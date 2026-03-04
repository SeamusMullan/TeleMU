"""REST endpoints for .tmu recording metadata."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from telemu.config import settings
from telemu.models import SessionMetadata
from telemu.recording import tmu_file

router = APIRouter(prefix="/recordings", tags=["recordings"])


class MetadataUpdateRequest(BaseModel):
    """Request body for updating user-editable metadata fields."""

    notes: str | None = None
    session_description: str | None = None
    setup_name: str | None = None


def _resolve_tmu_path(filename: str) -> Path:
    """Resolve a .tmu filename to an absolute path inside data_dir."""
    path = settings.data_dir / filename
    # Prevent path traversal
    if not path.resolve().is_relative_to(settings.data_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Recording not found")
    return path


@router.get("/{filename:path}/metadata", response_model=SessionMetadata)
async def get_recording_metadata(filename: str) -> SessionMetadata:
    """Read and return metadata from a .tmu file."""
    path = _resolve_tmu_path(filename)
    try:
        return tmu_file.read_header(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{filename:path}/metadata", response_model=SessionMetadata)
async def update_recording_metadata(
    filename: str, body: MetadataUpdateRequest
) -> SessionMetadata:
    """Update user-editable metadata fields in a .tmu file."""
    path = _resolve_tmu_path(filename)
    try:
        return tmu_file.update_metadata(
            path,
            notes=body.notes,
            session_description=body.session_description,
            setup_name=body.setup_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
