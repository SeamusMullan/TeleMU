"""Table inspection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from telemu.db import gateway
from telemu.models import ColumnInfo, ColumnStats, TableInfo

router = APIRouter(prefix="/tables", tags=["tables"])


def _get_conn(request: Request):
    """Get active DuckDB connection from app state."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise HTTPException(status_code=400, detail="No session open")
    return conn


@router.get("", response_model=list[TableInfo])
async def list_tables(request: Request) -> list[dict]:
    conn = _get_conn(request)
    names = gateway.list_tables(conn)
    return [
        {"name": name, "row_count": gateway.table_row_count(conn, name)} for name in names
    ]


@router.get("/{table}/schema", response_model=list[ColumnInfo])
async def get_schema(table: str, request: Request) -> list[dict]:
    conn = _get_conn(request)
    return gateway.table_schema(conn, table)


@router.get("/{table}/data")
async def get_data(
    table: str,
    request: Request,
    limit: int = Query(100, ge=1, le=100_000),
) -> dict:
    conn = _get_conn(request)
    columns, rows = gateway.preview_table(conn, table, limit)
    return {"columns": columns, "rows": rows, "row_count": len(rows)}


@router.get("/{table}/stats", response_model=list[ColumnStats])
async def get_stats(table: str, request: Request) -> list[dict]:
    conn = _get_conn(request)
    return gateway.all_column_stats(conn, table)
