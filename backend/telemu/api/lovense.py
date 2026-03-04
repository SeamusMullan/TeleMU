"""Lovense integration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from telemu.lovense import (
    LovenseClient,
    LovenseClientError,
    LovenseConnectRequest,
    LovenseConnectionStatus,
    LovenseFunctionRequest,
    LovenseLanResolveRequest,
)

router = APIRouter(prefix="/lovense", tags=["lovense"])


def _client(request: Request) -> LovenseClient:
    client = getattr(request.app.state, "lovense", None)
    if client is None:
        raise HTTPException(status_code=500, detail="Lovense client is not initialized")
    return client


@router.get("/status", response_model=LovenseConnectionStatus)
async def status(request: Request) -> LovenseConnectionStatus:
    return LovenseConnectionStatus(**_client(request).status())


@router.post("/connect", response_model=LovenseConnectionStatus)
async def connect(body: LovenseConnectRequest, request: Request) -> LovenseConnectionStatus:
    client = _client(request)
    client.configure(domain=body.domain, https_port=body.https_port)
    return LovenseConnectionStatus(**client.status())


@router.post("/resolve-lan")
async def resolve_lan(body: LovenseLanResolveRequest, request: Request) -> dict:
    client = _client(request)
    try:
        result = await client.resolve_lan(token=body.token, uid=body.uid)
    except LovenseClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return result


@router.post("/get-toys")
async def get_toys(request: Request) -> dict:
    client = _client(request)
    try:
        result = await client.get_toys()
    except LovenseClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return result


@router.post("/function")
async def function(body: LovenseFunctionRequest, request: Request) -> dict:
    client = _client(request)
    try:
        result = await client.function(
            action=body.action,
            time_sec=body.time_sec,
            toy=body.toy,
            stop_previous=body.stop_previous,
            loop_running_sec=body.loop_running_sec,
            loop_pause_sec=body.loop_pause_sec,
        )
    except LovenseClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return result


@router.post("/stop")
async def stop(request: Request, toy: str = "") -> dict:
    client = _client(request)
    try:
        result = await client.stop(toy=toy)
    except LovenseClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return result

