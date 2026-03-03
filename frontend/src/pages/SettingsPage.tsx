/** Settings page — connection, data directory, preferences. */

import { useEffect, useState } from "react";
import { api } from "../api/rest";
import type { HealthResponse } from "../api/types";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(console.error);
  }, []);

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-bold">Settings</h1>

      <div className="max-w-md space-y-4">
        <div className="rounded-lg bg-neutral-900 p-4">
          <h2 className="mb-2 text-sm font-bold text-neutral-300">Backend Status</h2>
          {health ? (
            <div className="space-y-1 font-mono text-sm text-neutral-400">
              <div>Version: {health.version}</div>
              <div>
                LMU:{" "}
                <span style={{ color: health.lmu_connected ? "var(--color-green)" : "var(--color-red)" }}>
                  {health.lmu_connected ? "Connected" : "Disconnected"}
                </span>
              </div>
              <div>WebSocket clients: {health.active_clients}</div>
            </div>
          ) : (
            <div className="text-sm text-neutral-500">Loading...</div>
          )}
        </div>
      </div>
    </div>
  );
}
