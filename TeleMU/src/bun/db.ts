/**
 * DuckDB wrapper — 1:1 port of LMUPI/lmupi/splitter.py.
 * All SQL queries match the Python original.
 */

import duckdb from "duckdb";
import type {
  TableInfo,
  ColumnInfo,
  ColumnStats,
  QueryResult,
  TableColumnMap,
} from "../shared/types";

const _NUMERIC_TYPE_FRAGMENTS = [
  "INT",
  "FLOAT",
  "DOUBLE",
  "DECIMAL",
  "NUMERIC",
  "BIGINT",
  "SMALL",
  "TINY",
  "HUGEINT",
  "REAL",
] as const;

function isNumericType(colType: string): boolean {
  const upper = colType.toUpperCase();
  return _NUMERIC_TYPE_FRAGMENTS.some((t) => upper.includes(t));
}

/** Promisify db.all / db.run */
function dbAll(
  db: duckdb.Database,
  sql: string,
  params: unknown[] = []
): Promise<Record<string, unknown>[]> {
  return new Promise((resolve, reject) => {
    db.all(sql, ...params, (err: Error | null, rows: Record<string, unknown>[]) => {
      if (err) reject(err);
      else resolve(rows ?? []);
    });
  });
}

function dbRun(
  db: duckdb.Database,
  sql: string,
  params: unknown[] = []
): Promise<void> {
  return new Promise((resolve, reject) => {
    db.run(sql, ...params, (err: Error | null) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

// ── Connection ──

let _db: duckdb.Database | null = null;

export function connect(dbPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    _db = new duckdb.Database(dbPath, { access_mode: "READ_ONLY" }, (err) => {
      if (err) {
        _db = null;
        reject(err);
      } else {
        resolve();
      }
    });
  });
}

export function disconnect(): void {
  if (_db) {
    _db.close();
    _db = null;
  }
}

function getDb(): duckdb.Database {
  if (!_db) throw new Error("No database connection");
  return _db;
}

// ── Table operations ──

export async function listTables(): Promise<string[]> {
  const rows = await dbAll(getDb(), "SHOW TABLES");
  return rows.map((r) => String(Object.values(r)[0]));
}

export async function tableRowCount(table: string): Promise<number> {
  const rows = await dbAll(getDb(), `SELECT COUNT(*) AS cnt FROM "${table}"`);
  return Number(rows[0]?.cnt ?? 0);
}

export async function listTablesWithCounts(): Promise<TableInfo[]> {
  const tables = await listTables();
  const result: TableInfo[] = [];
  for (const name of tables) {
    const rowCount = await tableRowCount(name);
    result.push({ name, rowCount });
  }
  return result;
}

export async function tableSchema(table: string): Promise<ColumnInfo[]> {
  const rows = await dbAll(getDb(), `PRAGMA table_info('${table}')`);
  return rows.map((r) => ({
    name: String(r.name),
    type: String(r.type),
    nullable: r.notnull === "YES" || r.notnull === false,
  }));
}

// ── Statistics ──

async function columnStats(
  table: string,
  column: string,
  colType: string
): Promise<ColumnStats> {
  const stats: ColumnStats = {
    column,
    type: colType,
    nulls: 0,
    distinct: 0,
    min: null,
    max: null,
    avg: null,
  };

  const countRows = await dbAll(
    getDb(),
    `SELECT COUNT(*) FILTER (WHERE "${column}" IS NULL) AS nulls, COUNT(DISTINCT "${column}") AS dist FROM "${table}"`
  );
  stats.nulls = Number(countRows[0]?.nulls ?? 0);
  stats.distinct = Number(countRows[0]?.dist ?? 0);

  if (isNumericType(colType)) {
    const aggRows = await dbAll(
      getDb(),
      `SELECT MIN("${column}") AS mn, MAX("${column}") AS mx, AVG("${column}") AS avg FROM "${table}"`
    );
    const row = aggRows[0];
    if (row) {
      stats.min = row.mn != null ? Number(row.mn) : null;
      stats.max = row.mx != null ? Number(row.mx) : null;
      stats.avg = row.avg != null ? Math.round(Number(row.avg) * 10000) / 10000 : null;
    }
  }

  return stats;
}

export async function allColumnStats(table: string): Promise<ColumnStats[]> {
  const schema = await tableSchema(table);
  const results: ColumnStats[] = [];
  for (const col of schema) {
    results.push(await columnStats(table, col.name, col.type));
  }
  return results;
}

// ── Data retrieval ──

export async function previewTable(
  table: string,
  limit: number = 100
): Promise<QueryResult> {
  const rows = await dbAll(getDb(), `SELECT * FROM "${table}" LIMIT ${limit}`);
  if (rows.length === 0) return { columns: [], rows: [] };
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c])),
  };
}

export async function filteredPreview(
  table: string,
  filters: Record<string, string>,
  limit: number = 100
): Promise<QueryResult> {
  const clauses: string[] = [];
  const params: unknown[] = [];
  for (const [col, pattern] of Object.entries(filters)) {
    if (pattern.trim()) {
      clauses.push(`CAST("${col}" AS VARCHAR) ILIKE ?`);
      params.push(`%${pattern}%`);
    }
  }
  const where = clauses.length > 0 ? ` WHERE ${clauses.join(" AND ")}` : "";
  const sql = `SELECT * FROM "${table}"${where} LIMIT ${limit}`;
  const rows = await dbAll(getDb(), sql, params);
  if (rows.length === 0) {
    // Still get columns from schema
    const schema = await tableSchema(table);
    return { columns: schema.map((c) => c.name), rows: [] };
  }
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c])),
  };
}

export async function executeSql(sql: string): Promise<QueryResult> {
  const rows = await dbAll(getDb(), sql);
  if (rows.length === 0) return { columns: [], rows: [] };
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c])),
  };
}

// ── Column utilities ──

export async function numericColumns(table: string): Promise<string[]> {
  const schema = await tableSchema(table);
  return schema.filter((c) => isNumericType(c.type)).map((c) => c.name);
}

export async function allNumericColumns(
  tables: string[]
): Promise<TableColumnMap> {
  const result: TableColumnMap = {};
  for (const t of tables) {
    result[t] = await numericColumns(t);
  }
  return result;
}

export async function fetchColumns(
  table: string,
  columns: string[]
): Promise<QueryResult> {
  const cols = columns.map((c) => `"${c}"`).join(", ");
  const sql = `SELECT ${cols} FROM "${table}"`;
  const rows = await dbAll(getDb(), sql);
  if (rows.length === 0) return { columns, rows: [] };
  const resultCols = Object.keys(rows[0]);
  return {
    columns: resultCols,
    rows: rows.map((r) => resultCols.map((c) => r[c])),
  };
}

export async function fetchJoinedColumns(
  tableColumns: TableColumnMap,
  on: string = "ts"
): Promise<QueryResult> {
  const allTables = Object.keys(tableColumns);
  if (allTables.length === 0) return { columns: [], rows: [] };

  // Only include tables that have the join column
  const tables: string[] = [];
  for (const tbl of allTables) {
    const schema = await tableSchema(tbl);
    if (schema.some((c) => c.name === on)) {
      tables.push(tbl);
    }
  }
  if (tables.length === 0) return { columns: [], rows: [] };

  // Build SELECT aliases and JOIN chain
  const selects: string[] = [`"${tables[0]}"."${on}" AS "${on}"`];
  for (const tbl of tables) {
    const cols = tableColumns[tbl];
    if (!cols) continue;
    for (const col of cols) {
      if (col === on) continue;
      selects.push(`"${tbl}"."${col}" AS "${tbl}.${col}"`);
    }
  }

  let fromClause = `"${tables[0]}"`;
  for (let i = 1; i < tables.length; i++) {
    fromClause += ` INNER JOIN "${tables[i]}" ON "${tables[0]}"."${on}" = "${tables[i]}"."${on}"`;
  }

  const sql = `SELECT ${selects.join(", ")} FROM ${fromClause}`;
  const rows = await dbAll(getDb(), sql);
  if (rows.length === 0) return { columns: [], rows: [] };
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c])),
  };
}

// ── Export ──

export async function exportCsv(
  outputPath: string,
  table?: string,
  sql?: string
): Promise<void> {
  if (sql) {
    await dbRun(
      getDb(),
      `COPY (${sql}) TO '${outputPath}' (FORMAT CSV, HEADER)`
    );
  } else if (table) {
    await dbRun(
      getDb(),
      `COPY "${table}" TO '${outputPath}' (FORMAT CSV, HEADER)`
    );
  }
}

export async function exportJson(
  outputPath: string,
  table?: string,
  sql?: string
): Promise<void> {
  if (sql) {
    await dbRun(
      getDb(),
      `COPY (${sql}) TO '${outputPath}' (FORMAT JSON)`
    );
  } else if (table) {
    await dbRun(
      getDb(),
      `COPY "${table}" TO '${outputPath}' (FORMAT JSON)`
    );
  }
}
