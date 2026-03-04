"""Streaming server control endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from telemu.models import StreamingStatus

router = APIRouter()


def _status(request: Request) -> StreamingStatus:
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


@router.get("/streaming/status", response_model=StreamingStatus)
async def streaming_status(request: Request) -> StreamingStatus:
    return _status(request)


@router.post("/streaming/start", response_model=StreamingStatus)
async def streaming_start(request: Request) -> StreamingStatus:
    streamer = getattr(request.app.state, "streamer", None)
    if streamer is not None and not streamer.running:
        await streamer.start()
    return _status(request)


@router.post("/streaming/stop", response_model=StreamingStatus)
async def streaming_stop(request: Request) -> StreamingStatus:
    streamer = getattr(request.app.state, "streamer", None)
    if streamer is not None and streamer.running:
        await streamer.stop()
    return _status(request)
