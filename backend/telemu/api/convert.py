"""Conversion endpoint — .tmu to DuckDB."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from telemu.config import settings
from telemu.recording.converter import convert_tmu_to_duckdb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/convert", tags=["convert"])


class ConvertRequest(BaseModel):
    """Request body for .tmu → DuckDB conversion."""

    files: list[str]  # list of .tmu filenames (relative to data_dir)
    output_dir: str | None = None  # output directory; defaults to data_dir
    auto_open: bool = False


class ConvertFileResult(BaseModel):
    filename: str
    output: str
    success: bool
    error: str | None = None


class ConvertResponse(BaseModel):
    results: list[ConvertFileResult]
    total: int
    converted: int


@router.get("/tmu-files")
async def list_tmu_files() -> list[dict]:
    """List available .tmu files in the data directory."""
    data_dir = settings.data_dir
    if not data_dir.exists():
        return []

    files = []
    for f in sorted(data_dir.glob("*.tmu"), key=lambda p: p.stat().st_mtime, reverse=True):
        files.append(
            {
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
            }
        )
    return files


@router.post("", response_model=ConvertResponse)
async def convert_tmu(req: ConvertRequest) -> ConvertResponse:
    """Convert one or more .tmu files to .duckdb."""
    data_dir = settings.data_dir
    out_dir = Path(req.output_dir) if req.output_dir else data_dir

    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    results: list[ConvertFileResult] = []
    converted = 0

    for filename in req.files:
        tmu_path = data_dir / filename

        if not tmu_path.exists():
            results.append(
                ConvertFileResult(
                    filename=filename,
                    output="",
                    success=False,
                    error=f"File not found: {filename}",
                )
            )
            continue

        if not tmu_path.suffix == ".tmu":
            results.append(
                ConvertFileResult(
                    filename=filename,
                    output="",
                    success=False,
                    error="Not a .tmu file",
                )
            )
            continue

        duckdb_name = tmu_path.with_suffix(".duckdb").name
        duckdb_path = out_dir / duckdb_name

        try:
            convert_tmu_to_duckdb(tmu_path, duckdb_path)
            results.append(
                ConvertFileResult(
                    filename=filename,
                    output=duckdb_name,
                    success=True,
                )
            )
            converted += 1
            logger.info("Converted %s → %s", filename, duckdb_name)
        except Exception as exc:
            logger.exception("Failed to convert %s", filename)
            results.append(
                ConvertFileResult(
                    filename=filename,
                    output="",
                    success=False,
                    error=str(exc),
                )
            )

    return ConvertResponse(
        results=results,
        total=len(req.files),
        converted=converted,
    )
