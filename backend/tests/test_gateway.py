"""Test DuckDB gateway functions."""

import tempfile
from pathlib import Path

import duckdb
import pytest

from telemu.db import gateway


@pytest.fixture
def test_db():
    """Create a temporary DuckDB with test data."""
    tmp = Path(tempfile.mktemp(suffix=".duckdb"))
    conn = duckdb.connect(str(tmp))
    conn.execute("CREATE TABLE speed (ts DOUBLE, value DOUBLE)")
    conn.execute("INSERT INTO speed VALUES (0.0, 100.0), (0.016, 105.0), (0.032, 110.0)")
    conn.execute("CREATE TABLE throttle (ts DOUBLE, value DOUBLE)")
    conn.execute("INSERT INTO throttle VALUES (0.0, 80.0), (0.016, 85.0), (0.032, 90.0)")
    conn.close()
    yield tmp
    tmp.unlink(missing_ok=True)


def test_connect(test_db):
    conn = gateway.connect(test_db)
    assert conn is not None
    conn.close()


def test_list_tables(test_db):
    conn = gateway.connect(test_db)
    tables = gateway.list_tables(conn)
    assert "speed" in tables
    assert "throttle" in tables
    conn.close()


def test_table_schema(test_db):
    conn = gateway.connect(test_db)
    schema = gateway.table_schema(conn, "speed")
    names = [col["name"] for col in schema]
    assert "ts" in names
    assert "value" in names
    conn.close()


def test_table_row_count(test_db):
    conn = gateway.connect(test_db)
    assert gateway.table_row_count(conn, "speed") == 3
    conn.close()


def test_preview_table(test_db):
    conn = gateway.connect(test_db)
    columns, rows = gateway.preview_table(conn, "speed", limit=2)
    assert columns == ["ts", "value"]
    assert len(rows) == 2
    conn.close()


def test_column_stats(test_db):
    conn = gateway.connect(test_db)
    stats = gateway.column_stats(conn, "speed", "value", "DOUBLE")
    assert stats["min"] == 100.0
    assert stats["max"] == 110.0
    assert stats["nulls"] == 0
    conn.close()


def test_execute_sql(test_db):
    conn = gateway.connect(test_db)
    cols, rows = gateway.execute_sql(conn, "SELECT * FROM speed WHERE value > 105")
    assert len(rows) == 1
    assert rows[0][1] == 110.0
    conn.close()


def test_numeric_columns(test_db):
    conn = gateway.connect(test_db)
    nums = gateway.numeric_columns(conn, "speed")
    assert "ts" in nums
    assert "value" in nums
    conn.close()


def test_fetch_joined_columns(test_db):
    conn = gateway.connect(test_db)
    cols, rows = gateway.fetch_joined_columns(
        conn,
        {"speed": ["value"], "throttle": ["value"]},
    )
    assert len(rows) == 3
    assert "speed.value" in cols
    assert "throttle.value" in cols
    conn.close()
