"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from telemu import __version__
from telemu.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    app = request.app
    reader = getattr(app.state, "reader", None)
    manager = getattr(app.state, "ws_manager", None)
    return HealthResponse(
        version=__version__,
        lmu_connected=reader.connected if reader else False,
        active_clients=manager.active_count if manager else 0,
    )
