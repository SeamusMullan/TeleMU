"""REST endpoints for telemetry streaming (client and server control)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from telemu.models import StreamingStatus
from telemu.streaming.protocol import DEFAULT_TCP_PORT

router = APIRouter(prefix="/streaming", tags=["streaming"])


# ── Request / Response models (engineer-side client) ──────────────────────────


class StreamConnectRequest(BaseModel):
    host: str = Field(..., min_length=1, description="Driver server IP or hostname")
    port: int = Field(DEFAULT_TCP_PORT, ge=1, le=65535, description="TCP control port")


class StreamingClientStatusResponse(BaseModel):
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


def _server_status(request: Request) -> StreamingStatus:
    streamer = getattr(request.app.state, "streamer", None)
    if streamer is None:
        return StreamingStatus()
    return StreamingStatus(
        running=streamer.running,
        clients_connected=streamer.clients_connected,
        data_rate_bps=streamer.data_rate_bps,
        host=streamer.host,
        discovery_port=streamer.discovery_port,
        telemetry_port=streamer.telemetry_port,
        control_port=streamer.control_port,
    )


# ── Engineer-side client endpoints ────────────────────────────────────────────


@router.get("/client/status", response_model=StreamingClientStatusResponse)
async def streaming_client_status(request: Request) -> StreamingClientStatusResponse:
    """Return the current state of the streaming client."""
    client = _get_client(request)
    return StreamingClientStatusResponse(**client.stats)


@router.post("/client/connect", response_model=StreamingClientStatusResponse)
async def streaming_connect(
    request: Request, body: StreamConnectRequest
) -> StreamingClientStatusResponse:
    """Start connecting to the driver's streaming server."""
    client = _get_client(request)
    await client.start(body.host, body.port)
    return StreamingClientStatusResponse(**client.stats)


@router.post("/client/disconnect", response_model=StreamingClientStatusResponse)
async def streaming_disconnect(request: Request) -> StreamingClientStatusResponse:
    """Disconnect from the driver's streaming server."""
    client = _get_client(request)
    await client.stop()
    return StreamingClientStatusResponse(**client.stats)


# ── Driver-side server endpoints ──────────────────────────────────────────────


@router.get("/status", response_model=StreamingStatus)
async def streaming_server_status(request: Request) -> StreamingStatus:
    """Return the current state of the streaming server."""
    return _server_status(request)


@router.post("/start", response_model=StreamingStatus)
async def streaming_start(request: Request) -> StreamingStatus:
    """Start the streaming server."""
    streamer = getattr(request.app.state, "streamer", None)
    if streamer is not None and not streamer.running:
        await streamer.start()
    return _server_status(request)


@router.post("/stop", response_model=StreamingStatus)
async def streaming_stop(request: Request) -> StreamingStatus:
    """Stop the streaming server."""
    streamer = getattr(request.app.state, "streamer", None)
    if streamer is not None and streamer.running:
        await streamer.stop()
    return _server_status(request)
