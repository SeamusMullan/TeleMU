/** SQL query editor — textarea, execute button, results table. */

import { useState, useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { api } from "../../api/rest";
import type { QueryResult } from "../../api/types";

export default function SqlQuery() {
  const [sql, setSql] = useState("SELECT * FROM telemetry LIMIT 100");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const handleExecute = async () => {
    if (!sql.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.query(sql);
      setResult(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleExecute();
    }
  };

  const virtualizer = useVirtualizer({
    count: result?.rows.length ?? 0,
    getScrollElement: () => resultsRef.current,
    estimateSize: () => 28,
    overscan: 10,
  });

  return (
    <div className="flex h-full flex-col">
      {/* SQL input */}
      <div className="border-b border-neutral-800 p-2">
        <textarea
          value={sql}
          onChange={(e) => setSql(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          placeholder="Enter SQL query... (Ctrl+Enter to execute)"
          className="w-full resize-none rounded border border-neutral-600 bg-neutral-800 px-2 py-1.5 font-mono text-xs text-neutral-200 outline-none focus:border-[var(--color-accent)]"
        />
        <div className="mt-1 flex items-center gap-2">
          <button
            onClick={handleExecute}
            disabled={loading || !sql.trim()}
            className="rounded px-3 py-1 text-xs font-bold text-black disabled:opacity-40"
            style={{ backgroundColor: "var(--color-accent)" }}
          >
            {loading ? "Running..." : "Execute"}
          </button>
          {result && (
            <span className="text-xs text-neutral-500">
              {result.row_count} rows in {result.elapsed_ms}ms
            </span>
          )}
        </div>
      </div>

      {error && <div className="px-2 py-1 text-xs text-red-400">{error}</div>}

      {/* Results */}
      <div ref={resultsRef} className="flex-1 overflow-auto">
        {result && (
          <table className="w-full border-collapse text-xs">
            <thead className="sticky top-0 z-10 bg-neutral-800">
              <tr>
                {result.columns.map((col) => (
                  <th
                    key={col}
                    className="border-b border-neutral-700 px-2 py-1.5 text-left font-mono font-bold text-neutral-300"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {virtualizer.getVirtualItems().length > 0 && (
                <tr>
                  <td
                    colSpan={result.columns.length}
                    style={{ height: virtualizer.getVirtualItems()[0]?.start ?? 0 }}
                  />
                </tr>
              )}
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = result.rows[virtualRow.index]!;
                return (
                  <tr key={virtualRow.index} className="hover:bg-neutral-800/50">
                    {row.map((cell, ci) => (
                      <td
                        key={ci}
                        className="border-b border-neutral-800/50 px-2 py-1 font-mono text-neutral-400"
                      >
                        {cell === null ? (
                          <span className="text-neutral-600">NULL</span>
                        ) : (
                          String(cell)
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })}
              {virtualizer.getVirtualItems().length > 0 && (
                <tr>
                  <td
                    colSpan={result.columns.length}
                    style={{
                      height:
                        virtualizer.getTotalSize() -
                        (virtualizer.getVirtualItems().at(-1)?.end ?? 0),
                    }}
                  />
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
