/** REST API client for TeleMU backend. */

import type {
  TableInfo,
  ColumnInfo,
  ColumnStats,
  QueryResult,
  SessionInfo,
  HealthResponse,
  TmuFileInfo,
  ConvertRequest,
  ConvertResponse,
  StreamingStatus,
} from "./types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => get<HealthResponse>("/health"),
  sessions: () => get<SessionInfo[]>("/sessions"),
  openSession: (filename: string) =>
    post<{ filename: string; tables: string[] }>(`/sessions/${filename}/open`, {}),
  tables: () => get<TableInfo[]>("/tables"),
  schema: (table: string) => get<ColumnInfo[]>(`/tables/${table}/schema`),
  data: (table: string, limit = 100) =>
    get<{ columns: string[]; rows: unknown[][]; row_count: number }>(
      `/tables/${table}/data?limit=${limit}`,
    ),
  stats: (table: string) => get<ColumnStats[]>(`/tables/${table}/stats`),
  query: (sql: string) => post<QueryResult>("/query", { sql }),
  tmuFiles: () => get<TmuFileInfo[]>("/convert/tmu-files"),
  convert: (req: ConvertRequest) => post<ConvertResponse>("/convert", req),
  streamingStatus: () => get<StreamingStatus>("/streaming/status"),
  streamingStart: () => post<StreamingStatus>("/streaming/start", {}),
  streamingStop: () => post<StreamingStatus>("/streaming/stop", {}),
};
