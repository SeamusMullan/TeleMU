/** Streaming client page — connect to a driver's streaming server. */

import { useEffect, useRef, useState } from "react";
import { api } from "../api/rest";
import type { StreamingClientStatus } from "../api/types";

const DEFAULT_PORT = 19742;
const POLL_INTERVAL_MS = 2000;

const STATE_COLORS: Record<string, string> = {
  connected: "var(--color-green)",
  connecting: "var(--color-yellow, #facc15)",
  reconnecting: "var(--color-yellow, #facc15)",
  idle: "var(--color-red)",
};

export default function StreamingPage() {
  const [host, setHost] = useState("");
  const [port, setPort] = useState(DEFAULT_PORT);
  const [status, setStatus] = useState<StreamingClientStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll status periodically so the UI stays in sync.
  const fetchStatus = () => {
    api
      .streamingClientStatus()
      .then((s) => {
        setStatus(s);
        setError(null);
      })
      .catch((e: unknown) => {
        if (e instanceof Error) setError(e.message);
      });
  };

  useEffect(() => {
    fetchStatus();
    pollRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current !== null) clearInterval(pollRef.current);
    };
  }, []);

  // Pre-fill host/port from current status when it arrives.
  useEffect(() => {
    if (status && status.host && !host) {
      setHost(status.host);
      setPort(status.port);
    }
  }, [status, host]);

  const handleConnect = async () => {
    if (!host.trim()) {
      setError("Please enter a host address.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const s = await api.streamingConnect({ host: host.trim(), port });
      setStatus(s);
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleDisconnect = async () => {
    setBusy(true);
    setError(null);
    try {
      const s = await api.streamingDisconnect();
      setStatus(s);
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const isActive =
    status?.state === "connected" ||
    status?.state === "connecting" ||
    status?.state === "reconnecting";

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-bold">Streaming Client</h1>
      <p className="mb-6 text-sm text-neutral-400">
        Connect to a driver's TeleMU streaming server to receive live telemetry.
      </p>

      <div className="max-w-lg space-y-4">
        {/* Connection form */}
        <div className="rounded-lg bg-neutral-900 p-4">
          <h2 className="mb-3 text-sm font-bold text-neutral-300">
            Driver Server
          </h2>

          <div className="mb-3 flex gap-2">
            <div className="flex-1">
              <label className="mb-1 block text-xs text-neutral-500">
                Host / IP
              </label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="192.168.1.10"
                disabled={busy || isActive}
                className="w-full rounded bg-neutral-800 px-3 py-1.5 font-mono text-sm text-neutral-100 outline-none focus:ring-1 focus:ring-[var(--color-accent)] disabled:opacity-50"
              />
            </div>
            <div className="w-24">
              <label className="mb-1 block text-xs text-neutral-500">
                TCP Port
              </label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(Number(e.target.value))}
                min={1}
                max={65535}
                disabled={busy || isActive}
                className="w-full rounded bg-neutral-800 px-3 py-1.5 font-mono text-sm text-neutral-100 outline-none focus:ring-1 focus:ring-[var(--color-accent)] disabled:opacity-50"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleConnect}
              disabled={busy || isActive}
              className="rounded bg-[var(--color-accent)] px-4 py-1.5 text-sm font-medium text-black hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Connect
            </button>
            <button
              onClick={handleDisconnect}
              disabled={busy || !isActive}
              className="rounded bg-neutral-700 px-4 py-1.5 text-sm font-medium text-neutral-100 hover:bg-neutral-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Disconnect
            </button>
          </div>

          {error && (
            <p className="mt-2 text-xs text-red-400">{error}</p>
          )}
        </div>

        {/* Connection status */}
        {status && (
          <div className="rounded-lg bg-neutral-900 p-4">
            <h2 className="mb-3 text-sm font-bold text-neutral-300">
              Connection Status
            </h2>
            <div className="space-y-2 font-mono text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{
                    backgroundColor:
                      STATE_COLORS[status.state] ?? "var(--color-red)",
                  }}
                />
                <span className="capitalize text-neutral-300">
                  {status.state}
                </span>
                {status.state !== "idle" && status.host && (
                  <span className="text-neutral-500">
                    → {status.host}:{status.port}
                  </span>
                )}
              </div>

              {status.state === "connected" && (
                <div className="mt-2 space-y-1 text-xs text-neutral-400">
                  <div>Channels: {status.channel_count}</div>
                  <div>Frames received: {status.rx_frames.toLocaleString()}</div>
                  <div>
                    Packets lost:{" "}
                    <span
                      style={{
                        color:
                          status.lost_packets > 0
                            ? "var(--color-yellow, #facc15)"
                            : "inherit",
                      }}
                    >
                      {status.lost_packets.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Info */}
        <div className="rounded-lg bg-neutral-900 p-4 text-xs text-neutral-500">
          <p className="mb-1 font-semibold text-neutral-400">Protocol notes</p>
          <ul className="list-inside list-disc space-y-0.5">
            <li>TCP control channel (default port 19742)</li>
            <li>UDP telemetry data (default port 19741)</li>
            <li>100 ms jitter buffer for smooth display</li>
            <li>Auto-reconnects with exponential back-off</li>
            <li>Packet loss is skipped — no stalling</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
