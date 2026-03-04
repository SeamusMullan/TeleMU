/** Schema browser — tree view of tables and their columns with type badges. */

import { useState, useEffect, useCallback } from "react";
import { useSessionStore } from "../../stores/sessionStore";
import { api } from "../../api/rest";
import type { ColumnInfo } from "../../api/types";

const TYPE_COLORS: Record<string, string> = {
  INTEGER: "var(--color-cyan)",
  BIGINT: "var(--color-cyan)",
  DOUBLE: "var(--color-blue)",
  FLOAT: "var(--color-blue)",
  VARCHAR: "var(--color-amber)",
  BOOLEAN: "var(--color-green)",
  TIMESTAMP: "var(--color-accent)",
};

export default function SchemaBrowser() {
  const { tables, activeSession } = useSessionStore();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [schemas, setSchemas] = useState<Record<string, ColumnInfo[]>>({});

  const toggleTable = useCallback(
    async (tableName: string) => {
      const next = new Set(expanded);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else {
        next.add(tableName);
        if (!schemas[tableName]) {
          try {
            const cols = await api.schema(tableName);
            setSchemas((prev) => ({ ...prev, [tableName]: cols }));
          } catch (err) {
            console.error("Failed to fetch schema for", tableName, err);
          }
        }
      }
      setExpanded(next);
    },
    [expanded, schemas],
  );

  // Reset when session changes
  useEffect(() => {
    setExpanded(new Set());
    setSchemas({});
  }, [activeSession]);

  if (!activeSession) {
    return (
      <div className="flex h-full items-center justify-center p-3 text-xs text-neutral-500">
        Open a session to browse schema
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-2">
      <div className="mb-2 text-xs font-bold text-neutral-300">Tables</div>
      {tables.map((table) => (
        <div key={table.name} className="mb-1">
          <button
            onClick={() => toggleTable(table.name)}
            className="flex w-full items-center gap-1 rounded px-2 py-1 text-xs text-neutral-300 hover:bg-neutral-800"
          >
            <span className="text-neutral-500">{expanded.has(table.name) ? "▼" : "▶"}</span>
            <span className="font-mono">{table.name}</span>
            <span className="ml-auto text-neutral-600">{table.row_count} rows</span>
          </button>
          {expanded.has(table.name) && schemas[table.name] && (
            <div className="ml-4 border-l border-neutral-800 pl-2">
              {schemas[table.name]!.map((col) => (
                <div key={col.name} className="flex items-center gap-2 py-0.5 text-xs">
                  <span className="font-mono text-neutral-400">{col.name}</span>
                  <span
                    className="rounded px-1 text-[10px] font-bold"
                    style={{
                      color: TYPE_COLORS[col.type] ?? "#888",
                      backgroundColor: `${TYPE_COLORS[col.type] ?? "#888"}20`,
                    }}
                  >
                    {col.type}
                  </span>
                  {col.nullable && <span className="text-[10px] text-neutral-600">null</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      {tables.length === 0 && (
        <div className="text-xs text-neutral-500">No tables found</div>
      )}
    </div>
  );
}
