"""Arbitrary SQL query endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from telemu.db import gateway
from telemu.models import QueryRequest, QueryResult

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResult)
async def run_query(body: QueryRequest, request: Request) -> QueryResult:
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise HTTPException(status_code=400, detail="No session open")

    t0 = time.perf_counter()
    try:
        columns, rows = gateway.execute_sql(conn, body.sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    elapsed = (time.perf_counter() - t0) * 1000

    return QueryResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        elapsed_ms=round(elapsed, 2),
    )
