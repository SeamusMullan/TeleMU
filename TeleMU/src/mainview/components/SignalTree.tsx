import React, { useState, useCallback, useEffect } from "react";
import { useApp } from "../store/AppContext";

export interface SelectedSignals {
  [table: string]: string[];
}

interface SignalTreeProps {
  onSelectionChange: (signals: SelectedSignals) => void;
  singleSelect?: boolean;
}

interface TableState {
  expanded: boolean;
  checkedCols: Set<string>;
}

export function SignalTree({ onSelectionChange, singleSelect = false }: SignalTreeProps) {
  const { state } = useApp();
  const [tableStates, setTableStates] = useState<Record<string, TableState>>({});

  // Initialize table states when numeric columns change
  useEffect(() => {
    const newStates: Record<string, TableState> = {};
    for (const table of Object.keys(state.numericColumns)) {
      newStates[table] = tableStates[table] ?? { expanded: true, checkedCols: new Set() };
    }
    setTableStates(newStates);
  }, [state.numericColumns]);

  const emitChange = useCallback(
    (states: Record<string, TableState>) => {
      const signals: SelectedSignals = {};
      for (const [table, ts] of Object.entries(states)) {
        if (ts.checkedCols.size > 0) {
          signals[table] = Array.from(ts.checkedCols);
        }
      }
      onSelectionChange(signals);
    },
    [onSelectionChange]
  );

  const toggleColumn = useCallback(
    (table: string, col: string) => {
      setTableStates((prev) => {
        let next: Record<string, TableState>;

        if (singleSelect) {
          // Clear all other selections
          next = {};
          for (const [t, ts] of Object.entries(prev)) {
            next[t] = { ...ts, checkedCols: new Set() };
          }
          if (!prev[table]?.checkedCols.has(col)) {
            next[table] = { ...next[table], checkedCols: new Set([col]) };
          }
        } else {
          next = { ...prev };
          const ts = { ...prev[table], checkedCols: new Set(prev[table].checkedCols) };
          if (ts.checkedCols.has(col)) {
            ts.checkedCols.delete(col);
          } else {
            ts.checkedCols.add(col);
          }
          next[table] = ts;
        }

        emitChange(next);
        return next;
      });
    },
    [singleSelect, emitChange]
  );

  const toggleTable = useCallback(
    (table: string) => {
      if (singleSelect) return;
      setTableStates((prev) => {
        const next = { ...prev };
        const cols = state.numericColumns[table] ?? [];
        const ts = { ...prev[table], checkedCols: new Set(prev[table].checkedCols) };
        const allChecked = cols.every((c) => ts.checkedCols.has(c));
        if (allChecked) {
          ts.checkedCols = new Set();
        } else {
          ts.checkedCols = new Set(cols);
        }
        next[table] = ts;
        emitChange(next);
        return next;
      });
    },
    [singleSelect, state.numericColumns, emitChange]
  );

  const toggleExpand = useCallback((table: string) => {
    setTableStates((prev) => ({
      ...prev,
      [table]: { ...prev[table], expanded: !prev[table]?.expanded },
    }));
  }, []);

  const tables = Object.keys(state.numericColumns);
  const totalSelected = Object.values(tableStates).reduce(
    (sum, ts) => sum + ts.checkedCols.size,
    0
  );

  return (
    <div className="flex flex-col h-full">
      <div className="text-xs text-telemu-text-dim mb-1">
        Signals{totalSelected > 0 ? ` (${totalSelected})` : ""}
      </div>
      <div className="flex-1 overflow-auto border border-telemu-border rounded bg-telemu-bg">
        {tables.map((table) => {
          const cols = state.numericColumns[table] ?? [];
          const ts = tableStates[table];
          if (!ts) return null;
          const hasTs = state.tablesWithTs.has(table);
          const allChecked = cols.length > 0 && cols.every((c) => ts.checkedCols.has(c));
          const someChecked = cols.some((c) => ts.checkedCols.has(c));

          return (
            <div key={table}>
              <div className="flex items-center gap-1 px-1 py-0.5 hover:bg-telemu-bg-light cursor-pointer">
                <button
                  onClick={() => toggleExpand(table)}
                  className="text-telemu-text-dim text-xs w-4 flex-shrink-0"
                >
                  {ts.expanded ? "▼" : "▶"}
                </button>
                {!singleSelect && (
                  <input
                    type="checkbox"
                    checked={allChecked}
                    ref={(el) => {
                      if (el) el.indeterminate = someChecked && !allChecked;
                    }}
                    onChange={() => toggleTable(table)}
                    className="accent-telemu-accent flex-shrink-0"
                  />
                )}
                <span
                  className={`text-xs truncate ${
                    hasTs ? "text-telemu-text" : "text-telemu-amber"
                  }`}
                  onClick={() => toggleExpand(table)}
                >
                  {table}
                  {!hasTs && " (no ts)"}
                </span>
              </div>
              {ts.expanded &&
                cols.map((col) => (
                  <div
                    key={`${table}.${col}`}
                    className="flex items-center gap-1 pl-6 pr-1 py-0.5 hover:bg-telemu-bg-light cursor-pointer"
                    onClick={() => toggleColumn(table, col)}
                  >
                    <input
                      type="checkbox"
                      checked={ts.checkedCols.has(col)}
                      onChange={() => toggleColumn(table, col)}
                      className="accent-telemu-accent flex-shrink-0"
                    />
                    <span className="text-xs text-telemu-text truncate">
                      {col}
                    </span>
                  </div>
                ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
