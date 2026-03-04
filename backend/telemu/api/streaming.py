"""REST endpoints for the engineer-side telemetry streaming client."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from telemu.streaming.protocol import DEFAULT_TCP_PORT

router = APIRouter(prefix="/streaming", tags=["streaming"])


# ── Request / Response models ─────────────────────────────────────────────────


class StreamConnectRequest(BaseModel):
    host: str = Field(..., min_length=1, description="Driver server IP or hostname")
    port: int = Field(DEFAULT_TCP_PORT, ge=1, le=65535, description="TCP control port")


class StreamingStatusResponse(BaseModel):
    state: str
    host: str
    port: int
    rx_frames: int
    lost_packets: int
    channel_count: int


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_client(request: Request):
    client = getattr(request.app.state, "streaming_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="Streaming client not available")
    return client


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/status", response_model=StreamingStatusResponse)
async def streaming_status(request: Request) -> StreamingStatusResponse:
    """Return the current state of the streaming client."""
    client = _get_client(request)
    return StreamingStatusResponse(**client.stats)


@router.post("/connect", response_model=StreamingStatusResponse)
async def streaming_connect(
    request: Request, body: StreamConnectRequest
) -> StreamingStatusResponse:
    """Start connecting to the driver's streaming server."""
    client = _get_client(request)
    await client.start(body.host, body.port)
    return StreamingStatusResponse(**client.stats)


@router.post("/disconnect", response_model=StreamingStatusResponse)
async def streaming_disconnect(request: Request) -> StreamingStatusResponse:
    """Disconnect from the driver's streaming server."""
    client = _get_client(request)
    await client.stop()
    return StreamingStatusResponse(**client.stats)
