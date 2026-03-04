/** Streaming server control panel — start/stop, status indicator. */

import { useEffect, useState, useCallback } from "react";
import { api } from "../../api/rest";
import type { StreamingServerStatus } from "../../api/types";

const POLL_INTERVAL_MS = 2000;

function formatRate(bps: number): string {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  return `${(bps / 1024).toFixed(1)} KB/s`;
}

export default function StreamingPanel() {
  const [status, setStatus] = useState<StreamingServerStatus | null>(null);
  const [busy, setBusy] = useState(false);

  const fetchStatus = useCallback(() => {
    api.streamingStatus().then(setStatus).catch(console.error);
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const handleStart = async () => {
    setBusy(true);
    try {
      const s = await api.streamingStart();
      setStatus(s);
    } catch (e) {
      console.error(e);
    } finally {
      setBusy(false);
    }
  };

  const handleStop = async () => {
    setBusy(true);
    try {
      const s = await api.streamingStop();
      setStatus(s);
    } catch (e) {
      console.error(e);
    } finally {
      setBusy(false);
    }
  };

  const running = status?.running ?? false;

  return (
    <div className="rounded-lg bg-neutral-900 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-bold text-neutral-300">LAN Streaming</span>
        <div className="flex items-center gap-1.5">
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: running ? "var(--color-green)" : "#555" }}
          />
          <span className="text-xs text-neutral-400">{running ? "Streaming" : "Stopped"}</span>
        </div>
      </div>

      {status && running && (
        <div className="mb-2 space-y-0.5 font-mono text-xs text-neutral-500">
          <div>
            Clients:{" "}
            <span className="text-neutral-300">{status.clients_connected}</span>
          </div>
          <div>
            Rate:{" "}
            <span className="text-neutral-300">{formatRate(status.data_rate_bps)}</span>
          </div>
          <div>
            Control port:{" "}
            <span className="text-neutral-300">{status.control_port}</span>
          </div>
        </div>
      )}

      <button
        onClick={running ? handleStop : handleStart}
        disabled={busy || status === null}
        className="w-full rounded px-3 py-1.5 text-xs font-bold transition-colors disabled:opacity-40"
        style={{
          backgroundColor: running ? "var(--color-red)" : "var(--color-accent)",
          color: "#000",
        }}
      >
        {busy ? "…" : running ? "Stop Streaming" : "Start Streaming"}
      </button>
    </div>
  );
}
