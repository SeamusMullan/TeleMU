"""Convert .tmu recordings to DuckDB for analysis.

Produces three tables:
    channels  – one row per sample, columns = ts + each channel name
    lap_markers – one row per lap marker
    metadata  – key/value session metadata
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import duckdb

from telemu.recording.tmu_format import TmuFrame, TmuHeader, iter_tmu

ProgressCallback = Callable[[int, int], None]  # (current, total)


def convert_tmu_to_duckdb(
    tmu_path: Path | str,
    duckdb_path: Path | str | None = None,
    on_progress: ProgressCallback | None = None,
) -> Path:
    """Convert a single .tmu file to .duckdb.

    Parameters
    ----------
    tmu_path : path to the .tmu file
    duckdb_path : destination path; defaults to ``<tmu_path>.duckdb``
    on_progress : optional callback ``(current_frame, total_frames)``

    Returns
    -------
    Path to the created .duckdb file.
    """
    tmu_path = Path(tmu_path)
    if duckdb_path is None:
        duckdb_path = tmu_path.with_suffix(".duckdb")
    duckdb_path = Path(duckdb_path)

    # First pass: collect all data (needed to know column names)
    header: TmuHeader | None = None
    frames: list[TmuFrame] = []
    for item in iter_tmu(tmu_path):
        if isinstance(item, TmuHeader):
            header = item
        else:
            frames.append(item)

    if header is None:
        header = TmuHeader()

    total = len(frames)

    # Discover all channel names across frames
    all_channels: list[str] = []
    seen: set[str] = set()
    if header.channels:
        all_channels = list(header.channels)
        seen = set(all_channels)
    for f in frames:
        for ch in f.channels:
            if ch not in seen:
                all_channels.append(ch)
                seen.add(ch)

    # Create DuckDB file
    if duckdb_path.exists():
        duckdb_path.unlink()
    conn = duckdb.connect(str(duckdb_path))

    try:
        _create_channels_table(conn, all_channels, frames, total, on_progress)
        _create_lap_markers_table(conn, frames)
        _create_metadata_table(conn, header)
    finally:
        conn.close()

    return duckdb_path


def _create_channels_table(
    conn: duckdb.DuckDBPyConnection,
    all_channels: list[str],
    frames: list[TmuFrame],
    total: int,
    on_progress: ProgressCallback | None,
) -> None:
    """Create the ``channels`` table with ts + one column per channel."""
    col_defs = ['"ts" DOUBLE']
    for ch in all_channels:
        col_defs.append(f'"{ch}" DOUBLE')

    conn.execute(f"CREATE TABLE channels ({', '.join(col_defs)})")

    if not frames:
        return

    placeholders = ", ".join(["?"] * (1 + len(all_channels)))
    insert_sql = f"INSERT INTO channels VALUES ({placeholders})"

    batch: list[tuple[Any, ...]] = []
    batch_size = 1000

    for idx, frame in enumerate(frames):
        row = [frame.ts] + [frame.channels.get(ch) for ch in all_channels]
        batch.append(tuple(row))

        if len(batch) >= batch_size:
            conn.executemany(insert_sql, batch)
            batch.clear()
            if on_progress:
                on_progress(idx + 1, total)

    if batch:
        conn.executemany(insert_sql, batch)

    if on_progress:
        on_progress(total, total)


def _create_lap_markers_table(
    conn: duckdb.DuckDBPyConnection,
    frames: list[TmuFrame],
) -> None:
    """Create the ``lap_markers`` table from frames that carry lap_marker data."""
    conn.execute(
        """CREATE TABLE lap_markers (
            ts DOUBLE,
            lap INTEGER,
            last_time VARCHAR,
            best_time VARCHAR,
            sector1 VARCHAR,
            sector2 VARCHAR,
            sector3 VARCHAR
        )"""
    )

    for frame in frames:
        if frame.lap_marker is None:
            continue
        lm = frame.lap_marker
        sectors = lm.get("sectors", [])
        conn.execute(
            "INSERT INTO lap_markers VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                frame.ts,
                lm.get("lap"),
                lm.get("last_time", ""),
                lm.get("best_time", ""),
                sectors[0] if len(sectors) > 0 else "",
                sectors[1] if len(sectors) > 1 else "",
                sectors[2] if len(sectors) > 2 else "",
            ],
        )


def _create_metadata_table(
    conn: duckdb.DuckDBPyConnection,
    header: TmuHeader,
) -> None:
    """Create a ``metadata`` table with key/value pairs from the header."""
    conn.execute("CREATE TABLE metadata (key VARCHAR, value VARCHAR)")

    meta = header.to_dict()
    for key, value in meta.items():
        if key == "channels":
            continue  # channels are represented as table columns
        str_val = str(value) if not isinstance(value, str) else value
        conn.execute("INSERT INTO metadata VALUES (?, ?)", [key, str_val])


def batch_convert(
    tmu_paths: list[Path | str],
    output_dir: Path | str | None = None,
    on_file_progress: Callable[[int, int, str], None] | None = None,
    on_frame_progress: ProgressCallback | None = None,
) -> list[Path]:
    """Convert multiple .tmu files to .duckdb.

    Parameters
    ----------
    tmu_paths : list of paths to .tmu files
    output_dir : directory for output files; defaults to same dir as each .tmu
    on_file_progress : callback ``(file_index, total_files, filename)``
    on_frame_progress : callback ``(current_frame, total_frames)``

    Returns
    -------
    List of created .duckdb paths.
    """
    results: list[Path] = []
    total_files = len(tmu_paths)

    for i, tmu_path in enumerate(tmu_paths):
        tmu_path = Path(tmu_path)
        if on_file_progress:
            on_file_progress(i, total_files, tmu_path.name)

        if output_dir:
            out = Path(output_dir) / tmu_path.with_suffix(".duckdb").name
        else:
            out = None

        result = convert_tmu_to_duckdb(tmu_path, out, on_frame_progress)
        results.append(result)

    if on_file_progress:
        on_file_progress(total_files, total_files, "")

    return results
