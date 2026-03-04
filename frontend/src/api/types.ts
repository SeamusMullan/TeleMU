/** TypeScript interfaces matching backend Pydantic models. */

// WebSocket server → client
export interface TelemetryMessage {
  type: "telemetry";
  ts: number;
  channels: Record<string, number>;
}

export interface StatusMessage {
  type: "status";
  drs: boolean;
  pit: boolean;
  flag: number;
  tc: boolean;
  abs: boolean;
}

export interface LapInfoMessage {
  type: "lap_info";
  lap: number;
  last_time: string;
  best_time: string;
  sectors: string[];
}

export interface EngineerMessage {
  type: "engineer";
  tool: string;
  data: Record<string, unknown>;
}

export type ServerMessage =
  | TelemetryMessage
  | StatusMessage
  | LapInfoMessage
  | EngineerMessage;

// REST API
export interface TableInfo {
  name: string;
  row_count: number;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
}

export interface ColumnStats {
  column: string;
  type: string;
  nulls: number;
  distinct: number;
  min: number | string | null;
  max: number | string | null;
  avg: number | null;
}

export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  elapsed_ms: number;
}

export interface SessionInfo {
  filename: string;
  path: string;
  size_bytes: number;
  tables: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
  lmu_connected: boolean;
  active_clients: number;
}

export interface StreamingStatus {
  running: boolean;
  clients_connected: number;
  data_rate_bps: number;
  host: string;
  discovery_port: number;
  telemetry_port: number;
  control_port: number;
}

// Convert .tmu → DuckDB
export interface TmuFileInfo {
  filename: string;
  path: string;
  size_bytes: number;
}

export interface ConvertRequest {
  files: string[];
  output_dir?: string;
  auto_open: boolean;
}

export interface ConvertFileResult {
  filename: string;
  output: string;
  success: boolean;
  error?: string;
}

export interface ConvertResponse {
  results: ConvertFileResult[];
  total: number;
  converted: number;
}

// Live recording
export interface RecordingStatus {
  active: boolean;
  filename: string;
  output_path: string;
  duration_seconds: number;
  file_size_bytes: number;
  data_rate_bps: number;
}

export interface StartRecordingRequest {
  output_dir?: string;
  filename?: string;
}
// Streaming client (engineer side)
export interface StreamingClientStatus {
  state: "idle" | "connecting" | "connected" | "reconnecting";
  host: string;
  port: number;
  rx_frames: number;
  lost_packets: number;
  channel_count: number;
}

export interface StreamConnectRequest {
  host: string;
  port: number;
}

// Streaming server (driver side)
export interface StreamingServerStatus {
  running: boolean;
  clients_connected: number;
  data_rate_bps: number;
  host: string;
  discovery_port: number;
  telemetry_port: number;
  control_port: number;
}

