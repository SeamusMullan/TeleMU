"""
Telemetry splitting logic — separate from the application layer.

Responsible for reading raw .duckdb telemetry files from LMU
and splitting them into organized, queryable data.
"""

from pathlib import Path

import duckdb


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open a read-only connection to a .duckdb telemetry file."""
    return duckdb.connect(str(db_path), read_only=True)


def list_tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Return all table names in the database."""
    rows = conn.execute("SHOW TABLES").fetchall()
    return [row[0] for row in rows]


def table_schema(conn: duckdb.DuckDBPyConnection, table: str) -> list[dict]:
    """Return column info for a table: name, type, nullable."""
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [
        {"name": row[1], "type": row[2], "nullable": row[3] == "YES"}
        for row in rows
    ]


def table_row_count(conn: duckdb.DuckDBPyConnection, table: str) -> int:
    """Return the number of rows in a table."""
    result = conn.execute(f"SELECT COUNT(*) FROM \"{table}\"").fetchone()
    return result[0] if result else 0


def preview_table(
    conn: duckdb.DuckDBPyConnection, table: str, limit: int = 100
) -> tuple[list[str], list[tuple]]:
    """Return (column_names, rows) for a table preview."""
    result = conn.execute(f"SELECT * FROM \"{table}\" LIMIT {limit}")
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    return columns, rows


def column_stats(
    conn: duckdb.DuckDBPyConnection, table: str, column: str, col_type: str
) -> dict:
    """Return statistics for a single column: min, max, avg, nulls, distinct."""
    stats: dict = {"column": column, "type": col_type}
    q = f'SELECT COUNT(*) FILTER (WHERE "{column}" IS NULL), COUNT(DISTINCT "{column}") FROM "{table}"'
    nulls, distinct = conn.execute(q).fetchone()
    stats["nulls"] = nulls
    stats["distinct"] = distinct

    is_numeric = any(
        t in col_type.upper()
        for t in ("INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "BIGINT", "SMALL", "TINY", "HUGEINT", "REAL")
    )
    if is_numeric:
        q = f'SELECT MIN("{column}"), MAX("{column}"), AVG("{column}") FROM "{table}"'
        mn, mx, avg = conn.execute(q).fetchone()
        stats["min"] = mn
        stats["max"] = mx
        stats["avg"] = round(avg, 4) if avg is not None else None
    else:
        stats["min"] = None
        stats["max"] = None
        stats["avg"] = None

    return stats


def all_column_stats(
    conn: duckdb.DuckDBPyConnection, table: str
) -> list[dict]:
    """Return per-column statistics for every column in the table."""
    schema = table_schema(conn, table)
    return [column_stats(conn, table, col["name"], col["type"]) for col in schema]


def execute_sql(
    conn: duckdb.DuckDBPyConnection, sql: str
) -> tuple[list[str], list[tuple]]:
    """Execute arbitrary SQL and return (columns, rows). Raises duckdb.Error on failure."""
    result = conn.execute(sql)
    if result.description is None:
        return [], []
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    return columns, rows


def export_csv(
    conn: duckdb.DuckDBPyConnection, table: str, output_path: str
) -> None:
    """Export an entire table to CSV using DuckDB COPY."""
    conn.execute(f"COPY \"{table}\" TO '{output_path}' (FORMAT CSV, HEADER)")


def export_query_csv(
    conn: duckdb.DuckDBPyConnection, sql: str, output_path: str
) -> None:
    """Export query results to CSV."""
    conn.execute(f"COPY ({sql}) TO '{output_path}' (FORMAT CSV, HEADER)")


def export_json(
    conn: duckdb.DuckDBPyConnection, table: str, output_path: str
) -> None:
    """Export an entire table to JSON using DuckDB COPY."""
    conn.execute(f"COPY \"{table}\" TO '{output_path}' (FORMAT JSON)")


def export_query_json(
    conn: duckdb.DuckDBPyConnection, sql: str, output_path: str
) -> None:
    """Export query results to JSON."""
    conn.execute(f"COPY ({sql}) TO '{output_path}' (FORMAT JSON)")


def import_csv(
    conn: duckdb.DuckDBPyConnection, csv_path: str, table_name: str
) -> None:
    """Import a CSV file as a new table in *conn* using DuckDB's read_csv_auto."""
    escaped_path = csv_path.replace("'", "''")
    escaped_table = table_name.replace('"', '""')
    conn.execute(
        f'CREATE TABLE "{escaped_table}" AS SELECT * FROM read_csv_auto(\'{escaped_path}\')'
    )


def import_json(
    conn: duckdb.DuckDBPyConnection, json_path: str, table_name: str
) -> None:
    """Import a JSON file as a new table in *conn* using DuckDB's read_json_auto."""
    escaped_path = json_path.replace("'", "''")
    escaped_table = table_name.replace('"', '""')
    conn.execute(
        f'CREATE TABLE "{escaped_table}" AS SELECT * FROM read_json_auto(\'{escaped_path}\')'
    )


_NUMERIC_TYPE_FRAGMENTS = (
    "INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC",
    "BIGINT", "SMALL", "TINY", "HUGEINT", "REAL",
)


def numeric_columns(conn: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    """Return names of numeric-typed columns in a table."""
    schema = table_schema(conn, table)
    return [
        col["name"]
        for col in schema
        if any(t in col["type"].upper() for t in _NUMERIC_TYPE_FRAGMENTS)
    ]


def fetch_columns(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    columns: list[str],
    limit: int = 0,
) -> tuple[list[str], list[tuple]]:
    """Fetch specific columns from a table. limit=0 means all rows."""
    cols = ", ".join(f'"{c}"' for c in columns)
    sql = f'SELECT {cols} FROM "{table}"'
    if limit > 0:
        sql += f" LIMIT {limit}"
    result = conn.execute(sql)
    col_names = [desc[0] for desc in result.description]
    rows = result.fetchall()
    return col_names, rows


def all_numeric_columns(
    conn: duckdb.DuckDBPyConnection, tables: list[str]
) -> dict[str, list[str]]:
    """Return {table: [numeric_col_names]} for every table in the list."""
    return {t: numeric_columns(conn, t) for t in tables}


def fetch_joined_columns(
    conn: duckdb.DuckDBPyConnection,
    table_columns: dict[str, list[str]],
    on: str = "ts",
) -> tuple[list[str], list[tuple]]:
    """JOIN multiple tables on a shared column and fetch requested columns.

    table_columns: {"Throttle": ["value"], "Speed": ["value"]}
    Returns aliased columns like ["Throttle.value", "Speed.value", "ts"] and rows.
    """
    # Only include tables that actually have the join column
    all_tables = list(table_columns.keys())
    if not all_tables:
        return [], []

    tables: list[str] = []
    for tbl in all_tables:
        schema = table_schema(conn, tbl)
        col_names_in_table = {col["name"] for col in schema}
        if on in col_names_in_table:
            tables.append(tbl)

    if not tables:
        return [], []

    # Build SELECT aliases and JOIN chain
    selects: list[str] = [f'"{tables[0]}"."{on}" AS "{on}"']
    for tbl in tables:
        for col in table_columns[tbl]:
            if col == on:
                continue
            selects.append(f'"{tbl}"."{col}" AS "{tbl}.{col}"')

    from_clause = f'"{tables[0]}"'
    for tbl in tables[1:]:
        from_clause += f' INNER JOIN "{tbl}" ON "{tables[0]}"."{on}" = "{tbl}"."{on}"'

    sql = f"SELECT {', '.join(selects)} FROM {from_clause}"
    result = conn.execute(sql)
    col_names = [desc[0] for desc in result.description]
    rows = result.fetchall()
    return col_names, rows


def filtered_preview(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    filters: dict[str, str],
    limit: int = 100,
) -> tuple[list[str], list[tuple]]:
    """Preview table data with ILIKE column filters (parameterized)."""
    clauses = []
    params = []
    for col, pattern in filters.items():
        if pattern.strip():
            clauses.append(f'CAST("{col}" AS VARCHAR) ILIKE ?')
            params.append(f"%{pattern}%")

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f'SELECT * FROM "{table}"{where} LIMIT {limit}'
    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    return columns, rows
