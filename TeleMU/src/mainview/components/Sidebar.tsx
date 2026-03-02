import React from "react";
import { useApp } from "../store/AppContext";

export function Sidebar() {
  const { state, dispatch } = useApp();

  return (
    <div className="w-48 flex-shrink-0 border-r border-telemu-border bg-telemu-bg overflow-auto">
      <div className="p-2">
        <div className="text-xs font-semibold text-telemu-accent truncate mb-1">
          {state.dbFileName}
        </div>
        {state.tables.map((t) => (
          <div
            key={t.name}
            onClick={() => {
              dispatch({ type: "SET_TABLE", payload: t.name });
              dispatch({ type: "SET_TAB", payload: "explorer" });
            }}
            className={`flex items-center justify-between px-2 py-1 rounded cursor-pointer text-xs ${
              state.currentTable === t.name
                ? "bg-telemu-selection text-telemu-accent"
                : "text-telemu-text hover:bg-telemu-bg-light"
            }`}
          >
            <span className="truncate">{t.name}</span>
            <span className="text-telemu-text-dim ml-1 flex-shrink-0">
              {t.rowCount.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
