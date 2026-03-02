import React, { useCallback } from "react";
import { AppProvider, useApp, type TabId } from "./store/AppContext";
import { rpcRequest } from "./hooks/useRPC";
import { Sidebar } from "./components/Sidebar";
import { ExplorerTab } from "./components/ExplorerTab";
import { SqlTab } from "./components/SqlTab";
import { SignalAnalyzer } from "./components/SignalAnalyzer";
import { TrackViewer } from "./components/TrackViewer";
import { AdvancedAnalysis } from "./components/AdvancedAnalysis";

const TABS: { id: TabId; label: string }[] = [
  { id: "explorer", label: "Explorer" },
  { id: "sql", label: "SQL Query" },
  { id: "analyzer", label: "Signal Analyzer" },
  { id: "track", label: "Track Viewer" },
  { id: "advanced", label: "Advanced" },
];

function AppInner() {
  const { state, dispatch } = useApp();

  const handleOpen = useCallback(async () => {
    try {
      const path = await rpcRequest("openFileDialog");
      if (!path) return;
      const result = await rpcRequest("connect", { path });
      const fileName = path.split("/").pop() ?? path;
      dispatch({
        type: "CONNECT",
        payload: { path, fileName, tables: result.tables },
      });

      // Fetch numeric columns and ts info for all tables
      const tableNames = result.tables.map((t) => t.name);
      const numCols = await rpcRequest("allNumericColumns", {
        tables: tableNames,
      });
      dispatch({ type: "SET_NUMERIC_COLUMNS", payload: numCols });

      // Check which tables have ts
      const withTs = new Set<string>();
      for (const t of tableNames) {
        const schema = await rpcRequest("tableSchema", { table: t });
        if (schema.some((c) => c.name === "ts")) withTs.add(t);
      }
      dispatch({ type: "SET_TABLES_WITH_TS", payload: withTs });
    } catch (err) {
      console.error("Failed to open database:", err);
    }
  }, [dispatch]);

  const handleExport = useCallback(
    async (format: "csv" | "json") => {
      if (!state.connected || !state.currentTable) return;
      const ext = format === "csv" ? "csv" : "json";
      const path = await rpcRequest("saveFileDialog", {
        defaultName: `${state.currentTable}.${ext}`,
      });
      if (!path) return;
      try {
        if (format === "csv") {
          await rpcRequest("exportCsv", {
            table: state.currentTable,
            outputPath: path,
          });
        } else {
          await rpcRequest("exportJson", {
            table: state.currentTable,
            outputPath: path,
          });
        }
      } catch (err) {
        console.error(`Export ${format} failed:`, err);
      }
    },
    [state.connected, state.currentTable]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-1 px-2 py-1 bg-telemu-bg-light border-b border-telemu-border">
        <button
          onClick={handleOpen}
          className="px-3 py-1 rounded text-telemu-text hover:bg-telemu-bg-lighter hover:text-telemu-accent border border-transparent hover:border-telemu-border text-sm font-medium"
        >
          Open
        </button>
        <button
          onClick={() => handleExport("csv")}
          disabled={!state.connected}
          className="px-3 py-1 rounded text-telemu-text hover:bg-telemu-bg-lighter hover:text-telemu-accent border border-transparent hover:border-telemu-border text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Export CSV
        </button>
        <button
          onClick={() => handleExport("json")}
          disabled={!state.connected}
          className="px-3 py-1 rounded text-telemu-text hover:bg-telemu-bg-lighter hover:text-telemu-accent border border-transparent hover:border-telemu-border text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Export JSON
        </button>
        <div className="flex-1" />
        {state.connected && (
          <span className="text-telemu-text-dim text-xs truncate max-w-[300px]">
            {state.dbFileName}
          </span>
        )}
      </div>

      {/* Main area: sidebar + tabs */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        {state.connected && <Sidebar />}

        {/* Tab content area */}
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Tab bar */}
          {state.connected && (
            <div className="flex bg-telemu-bg-light border-b border-telemu-border">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() =>
                    dispatch({ type: "SET_TAB", payload: tab.id })
                  }
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    state.activeTab === tab.id
                      ? "text-telemu-accent border-telemu-accent bg-telemu-bg"
                      : "text-telemu-text-dim border-transparent hover:text-telemu-text hover:bg-telemu-bg-lighter"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}

          {/* Tab panels */}
          <div className="flex-1 overflow-hidden">
            {!state.connected ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <h1 className="text-2xl font-bold text-telemu-accent mb-2">
                    TeleMU
                  </h1>
                  <p className="text-telemu-text-dim mb-4">
                    Telemetry Explorer
                  </p>
                  <button
                    onClick={handleOpen}
                    className="px-6 py-2 bg-telemu-accent text-telemu-text-bright rounded font-medium hover:bg-telemu-accent-hover active:bg-telemu-accent-pressed"
                  >
                    Open Database
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div
                  className={
                    state.activeTab === "explorer" ? "h-full" : "hidden"
                  }
                >
                  <ExplorerTab />
                </div>
                <div
                  className={state.activeTab === "sql" ? "h-full" : "hidden"}
                >
                  <SqlTab />
                </div>
                <div
                  className={
                    state.activeTab === "analyzer" ? "h-full" : "hidden"
                  }
                >
                  <SignalAnalyzer />
                </div>
                <div
                  className={state.activeTab === "track" ? "h-full" : "hidden"}
                >
                  <TrackViewer />
                </div>
                <div
                  className={
                    state.activeTab === "advanced" ? "h-full" : "hidden"
                  }
                >
                  <AdvancedAnalysis />
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  );
}
