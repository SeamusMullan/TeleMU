import React, { useState, useEffect, useCallback, useRef } from "react";
import { useApp } from "../store/AppContext";
import { rpcRequest } from "../hooks/useRPC";
import { DataTable } from "./DataTable";
import type { ColumnInfo, ColumnStats, QueryResult } from "../../shared/types";

type SubTab = "schema" | "stats";

export function ExplorerTab() {
  const { state } = useApp();
  const [subTab, setSubTab] = useState<SubTab>("schema");
  const [limit, setLimit] = useState(100);
  const [schema, setSchema] = useState<ColumnInfo[]>([]);
  const [stats, setStats] = useState<ColumnStats[]>([]);
  const [data, setData] = useState<QueryResult>({ columns: [], rows: [] });
  const [filters, setFilters] = useState<Record<string, string>>({});
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Load table data when currentTable changes
  useEffect(() => {
    if (!state.currentTable) return;
    const table = state.currentTable;

    rpcRequest("tableSchema", { table }).then(setSchema);
    rpcRequest("allColumnStats", { table }).then(setStats);
    setFilters({});
    loadData(table, {}, limit);
  }, [state.currentTable]);

  // Reload on limit change
  useEffect(() => {
    if (!state.currentTable) return;
    loadData(state.currentTable, filters, limit);
  }, [limit]);

  const loadData = useCallback(
    async (table: string, f: Record<string, string>, lim: number) => {
      const effectiveLimit = lim === 0 ? 999_999_999 : lim;
      const hasFilters = Object.values(f).some((v) => v.trim());
      const result = hasFilters
        ? await rpcRequest("filteredPreview", { table, filters: f, limit: effectiveLimit })
        : await rpcRequest("previewTable", { table, limit: effectiveLimit });
      setData(result);
    },
    []
  );

  const handleFilterChange = useCallback(
    (col: string, value: string) => {
      setFilters((prev) => {
        const next = { ...prev };
        if (value.trim()) {
          next[col] = value;
        } else {
          delete next[col];
        }

        // Debounce the actual query
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
          if (state.currentTable) {
            loadData(state.currentTable, next, limit);
          }
        }, 300);

        return next;
      });
    },
    [state.currentTable, limit, loadData]
  );

  const clearFilters = useCallback(() => {
    setFilters({});
    if (state.currentTable) loadData(state.currentTable, {}, limit);
  }, [state.currentTable, limit, loadData]);

  if (!state.currentTable) {
    return (
      <div className="flex items-center justify-center h-full text-telemu-text-dim text-sm">
        Select a table from the sidebar
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-2 gap-2">
      {/* Top bar */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-telemu-text-dim">Table:</span>
        <span className="text-xs text-telemu-text font-medium">{state.currentTable}</span>
        <div className="flex-1" />
        <span className="text-xs text-telemu-text-dim">Rows:</span>
        <select
          value={limit}
          onChange={(e) => setLimit(e.target.value === "0" ? 0 : parseInt(e.target.value))}
          className="bg-telemu-bg-input border border-telemu-border rounded px-2 py-0.5 text-xs text-telemu-text"
        >
          <option value={100}>100</option>
          <option value={500}>500</option>
          <option value={1000}>1000</option>
          <option value={0}>All</option>
        </select>
      </div>

      {/* Schema / Stats sub-tabs */}
      <div className="flex gap-1 border-b border-telemu-border">
        <button
          onClick={() => setSubTab("schema")}
          className={`px-3 py-1 text-xs border-b-2 ${
            subTab === "schema"
              ? "text-telemu-accent border-telemu-accent"
              : "text-telemu-text-dim border-transparent hover:text-telemu-text"
          }`}
        >
          Schema
        </button>
        <button
          onClick={() => setSubTab("stats")}
          className={`px-3 py-1 text-xs border-b-2 ${
            subTab === "stats"
              ? "text-telemu-accent border-telemu-accent"
              : "text-telemu-text-dim border-transparent hover:text-telemu-text"
          }`}
        >
          Statistics
        </button>
      </div>

      {/* Schema / Stats content */}
      <div className="max-h-[200px] overflow-auto">
        {subTab === "schema" ? (
          <DataTable
            columns={["Column", "Type", "Nullable"]}
            rows={schema.map((c) => [c.name, c.type, c.nullable ? "YES" : "NO"])}
          />
        ) : (
          <DataTable
            columns={["Column", "Type", "Min", "Max", "Avg", "Nulls"]}
            rows={stats.map((s) => [
              s.column,
              s.type,
              s.min != null ? String(s.min) : "",
              s.max != null ? String(s.max) : "",
              s.avg != null ? String(s.avg) : "",
              String(s.nulls),
            ])}
          />
        )}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-1 overflow-x-auto flex-shrink-0">
        {schema.map((col) => (
          <input
            key={col.name}
            type="text"
            placeholder={col.name}
            value={filters[col.name] ?? ""}
            onChange={(e) => handleFilterChange(col.name, e.target.value)}
            className="bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text min-w-[80px] max-w-[160px] focus:border-telemu-accent outline-none"
          />
        ))}
        {Object.keys(filters).length > 0 && (
          <button
            onClick={clearFilters}
            className="text-xs text-telemu-text-dim hover:text-telemu-accent px-2 flex-shrink-0"
          >
            Clear
          </button>
        )}
      </div>

      {/* Data table */}
      <div className="flex-1 overflow-hidden">
        <DataTable columns={data.columns} rows={data.rows} />
      </div>
    </div>
  );
}
