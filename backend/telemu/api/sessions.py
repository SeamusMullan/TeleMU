"""Session management endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from telemu.db import gateway, session_store
from telemu.models import SessionInfo

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionInfo])
async def list_sessions() -> list[dict]:
    return session_store.list_sessions()


@router.get("/{filename:path}", response_model=SessionInfo)
async def get_session(filename: str) -> dict:
    sessions = session_store.list_sessions()
    for s in sessions:
        if s["filename"] == filename:
            return s
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/{filename:path}/open")
async def open_session(filename: str) -> dict:
    """Open a session and return its tables."""
    sessions = session_store.list_sessions()
    for s in sessions:
        if s["filename"] == filename:
            conn = gateway.connect(s["path"])
            tables = gateway.list_tables(conn)
            conn.close()
            return {"filename": filename, "tables": tables}
    raise HTTPException(status_code=404, detail="Session not found")
