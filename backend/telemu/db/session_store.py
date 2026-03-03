"""Session file management — discovers and manages .duckdb files."""

from __future__ import annotations

from pathlib import Path

from telemu.config import settings
from telemu.db import gateway


def list_sessions(data_dir: Path | None = None) -> list[dict]:
    """List all .duckdb session files in the data directory."""
    directory = data_dir or settings.data_dir
    if not directory.exists():
        return []

    sessions = []
    for f in sorted(directory.glob("*.duckdb"), key=lambda p: p.stat().st_mtime, reverse=True):
        info = {
            "filename": f.name,
            "path": str(f),
            "size_bytes": f.stat().st_size,
        }
        try:
            conn = gateway.connect(f)
            info["tables"] = gateway.list_tables(conn)
            conn.close()
        except Exception:
            info["tables"] = []
        sessions.append(info)
    return sessions


def get_session(path: str) -> dict | None:
    """Get info for a specific session file."""
    p = Path(path)
    if not p.exists():
        return None
    info = {
        "filename": p.name,
        "path": str(p),
        "size_bytes": p.stat().st_size,
    }
    try:
        conn = gateway.connect(p)
        info["tables"] = gateway.list_tables(conn)
        conn.close()
    except Exception:
        info["tables"] = []
    return info
