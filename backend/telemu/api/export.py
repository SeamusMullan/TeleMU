"""Export endpoints for CSV/JSON."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from telemu.db import gateway

router = APIRouter(prefix="/export", tags=["export"])


def _get_conn(request: Request):
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise HTTPException(status_code=400, detail="No session open")
    return conn


@router.get("/{table}/csv")
async def export_table_csv(table: str, request: Request) -> FileResponse:
    conn = _get_conn(request)
    tmp = Path(tempfile.mktemp(suffix=".csv"))
    try:
        gateway.export_csv(conn, table, str(tmp))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return FileResponse(tmp, filename=f"{table}.csv", media_type="text/csv")


@router.get("/{table}/json")
async def export_table_json(table: str, request: Request) -> FileResponse:
    conn = _get_conn(request)
    tmp = Path(tempfile.mktemp(suffix=".json"))
    try:
        gateway.export_json(conn, table, str(tmp))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return FileResponse(tmp, filename=f"{table}.json", media_type="application/json")
