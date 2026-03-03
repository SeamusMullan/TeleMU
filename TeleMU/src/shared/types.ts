import type { ElectrobunRPCSchema, RPCSchema } from "electrobun/bun";

// ── Data types ──

export interface TableInfo {
  name: string;
  rowCount: number;
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
}

export interface TableColumnMap {
  [table: string]: string[];
}

export interface RecordingStatus {
  recording: boolean;
  path: string | null;
  startTime: number | null;
  size: number;
}

// ── RPC Schema ──

export interface TeleMURPCSchema extends ElectrobunRPCSchema {
  bun: RPCSchema<{
    requests: {
      openFileDialog: {
        params: undefined;
        response: string | null;
      };
      saveFileDialog: {
        params: { defaultName: string };
        response: string | null;
      };
      connect: {
        params: { path: string };
        response: { tables: TableInfo[] };
      };
      disconnect: {
        params: undefined;
        response: void;
      };
      tableSchema: {
        params: { table: string };
        response: ColumnInfo[];
      };
      allColumnStats: {
        params: { table: string };
        response: ColumnStats[];
      };
      previewTable: {
        params: { table: string; limit: number };
        response: QueryResult;
      };
      filteredPreview: {
        params: { table: string; filters: Record<string, string>; limit: number };
        response: QueryResult;
      };
      executeSql: {
        params: { sql: string };
        response: QueryResult;
      };
      allNumericColumns: {
        params: { tables: string[] };
        response: TableColumnMap;
      };
      fetchColumns: {
        params: { table: string; columns: string[] };
        response: QueryResult;
      };
      fetchJoinedColumns: {
        params: { tableColumns: TableColumnMap; on: string };
        response: QueryResult;
      };
      exportCsv: {
        params: { table?: string; sql?: string; outputPath: string };
        response: void;
      };
      exportJson: {
        params: { table?: string; sql?: string; outputPath: string };
        response: void;
      };
      startRecording: {
        params: { outputDir?: string; filename?: string };
        response: { path: string };
      };
      stopRecording: {
        params: undefined;
        response: { path: string; size: number; duration: number };
      };
      getRecordingStatus: {
        params: undefined;
        response: RecordingStatus;
      };
    };
    messages: {};
  }>;
  webview: RPCSchema<{
    requests: {};
    messages: {};
  }>;
}
