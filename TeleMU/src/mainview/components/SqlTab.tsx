import React, { useState, useCallback, useRef } from "react";
import { rpcRequest } from "../hooks/useRPC";
import { DataTable } from "./DataTable";
import type { QueryResult } from "../../shared/types";

export function SqlTab() {
  const [sql, setSql] = useState("");
  const [result, setResult] = useState<QueryResult>({ columns: [], rows: [] });
  const [status, setStatus] = useState("");
  const [isError, setIsError] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const runQuery = useCallback(async () => {
    const query = sql.trim();
    if (!query) return;

    const t0 = performance.now();
    try {
      const res = await rpcRequest("executeSql", { sql: query });
      const elapsed = ((performance.now() - t0) / 1000).toFixed(3);
      setResult(res);
      setStatus(`${res.rows.length} rows in ${elapsed}s`);
      setIsError(false);
    } catch (err) {
      const elapsed = ((performance.now() - t0) / 1000).toFixed(3);
      setResult({ columns: [], rows: [] });
      setStatus(err instanceof Error ? err.message : String(err));
      setIsError(true);
    }
  }, [sql]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        runQuery();
      }
    },
    [runQuery]
  );

  return (
    <div className="flex flex-col h-full p-2 gap-2">
      {/* SQL editor */}
      <textarea
        ref={textareaRef}
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter SQL query..."
        className="bg-telemu-bg-input border border-telemu-border rounded px-3 py-2 text-sm text-telemu-text font-mono resize-none h-[140px] focus:border-telemu-accent outline-none"
        spellCheck={false}
      />

      {/* Run bar */}
      <div className="flex items-center gap-2">
        <button
          onClick={runQuery}
          className="px-4 py-1.5 bg-telemu-accent text-telemu-text-bright rounded text-sm font-medium hover:bg-telemu-accent-hover active:bg-telemu-accent-pressed"
        >
          Run (Ctrl+Enter)
        </button>
        {status && (
          <span
            className={`text-xs ${
              isError ? "text-telemu-red" : "text-telemu-green"
            }`}
          >
            {status}
          </span>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-hidden">
        <DataTable columns={result.columns} rows={result.rows} />
      </div>
    </div>
  );
}
