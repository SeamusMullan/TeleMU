/** Settings page — backend status, layout profiles, connection settings, preferences. */

import { useEffect, useState, useRef } from "react";
import { api } from "../api/rest";
import type { HealthResponse } from "../api/types";
import { useLayoutStore, type LayoutProfile } from "../stores/layoutStore";
import { useSettingsStore } from "../stores/settingsStore";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(console.error);
  }, []);

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-bold">Settings</h1>
      <div className="max-w-2xl space-y-4">
        <BackendStatus health={health} />
        <LayoutProfiles />
        <ConnectionSettings />
        <Preferences />
      </div>
    </div>
  );
}

function BackendStatus({ health }: { health: HealthResponse | null }) {
  return (
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
  );
}

function LayoutProfiles() {
  const { profiles, activeProfileId, setActiveProfile, deleteProfile, resetToDefault, importProfile } =
    useLayoutStore();
  const fileRef = useRef<HTMLInputElement>(null);

  const handleExport = () => {
    const profile = profiles.find((p) => p.id === activeProfileId);
    if (!profile) return;
    const blob = new Blob([JSON.stringify(profile, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `telemu-layout-${profile.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const profile = JSON.parse(reader.result as string) as LayoutProfile;
        importProfile(profile);
      } catch {
        alert("Invalid layout file");
      }
    };
    reader.readAsText(file);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="rounded-lg bg-neutral-900 p-4">
      <h2 className="mb-2 text-sm font-bold text-neutral-300">Layout Profiles</h2>
      <div className="space-y-2">
        {profiles.map((p) => (
          <div key={p.id} className="flex items-center gap-2">
            <button
              onClick={() => setActiveProfile(p.id)}
              className={`flex-1 rounded px-3 py-1.5 text-left text-xs transition-colors ${
                p.id === activeProfileId
                  ? "border border-[var(--color-accent)] bg-neutral-800 text-white"
                  : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {p.name}
              {p.id === activeProfileId && (
                <span className="ml-2 text-[10px] text-[var(--color-accent)]">active</span>
              )}
            </button>
            {profiles.length > 1 && (
              <button
                onClick={() => deleteProfile(p.id)}
                className="text-xs text-neutral-600 hover:text-red-400"
                title="Delete profile"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button
          onClick={handleExport}
          className="rounded bg-neutral-800 px-3 py-1 text-xs text-neutral-400 hover:text-neutral-200"
        >
          Export
        </button>
        <button
          onClick={() => fileRef.current?.click()}
          className="rounded bg-neutral-800 px-3 py-1 text-xs text-neutral-400 hover:text-neutral-200"
        >
          Import
        </button>
        <input ref={fileRef} type="file" accept=".json" onChange={handleImport} className="hidden" />
        <button
          onClick={resetToDefault}
          className="rounded bg-neutral-800 px-3 py-1 text-xs text-neutral-400 hover:text-red-400"
        >
          Reset All
        </button>
      </div>
    </div>
  );
}

function ConnectionSettings() {
  const { backendUrl, wsUrl, setBackendUrl, setWsUrl } = useSettingsStore();

  return (
    <div className="rounded-lg bg-neutral-900 p-4">
      <h2 className="mb-2 text-sm font-bold text-neutral-300">Connection</h2>
      <div className="space-y-2">
        <div>
          <label className="mb-0.5 block text-xs text-neutral-400">Backend URL Override</label>
          <input
            type="text"
            value={backendUrl}
            onChange={(e) => setBackendUrl(e.target.value)}
            placeholder="Default: /api"
            className="w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-1.5 text-xs text-neutral-200 outline-none"
          />
        </div>
        <div>
          <label className="mb-0.5 block text-xs text-neutral-400">WebSocket URL Override</label>
          <input
            type="text"
            value={wsUrl}
            onChange={(e) => setWsUrl(e.target.value)}
            placeholder="Default: ws://localhost:8000/ws"
            className="w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-1.5 text-xs text-neutral-200 outline-none"
          />
        </div>
      </div>
    </div>
  );
}

function Preferences() {
  const { historySize, reconnectDelay, defaultEditMode, setHistorySize, setReconnectDelay, setDefaultEditMode } =
    useSettingsStore();

  return (
    <div className="rounded-lg bg-neutral-900 p-4">
      <h2 className="mb-2 text-sm font-bold text-neutral-300">Preferences</h2>
      <div className="space-y-2">
        <div>
          <label className="mb-0.5 block text-xs text-neutral-400">Telemetry History Size</label>
          <input
            type="number"
            value={historySize}
            onChange={(e) => setHistorySize(Number(e.target.value))}
            min={50}
            max={1000}
            className="w-32 rounded border border-neutral-600 bg-neutral-800 px-2 py-1.5 text-xs text-neutral-200 outline-none"
          />
        </div>
        <div>
          <label className="mb-0.5 block text-xs text-neutral-400">Reconnect Delay (ms)</label>
          <input
            type="number"
            value={reconnectDelay}
            onChange={(e) => setReconnectDelay(Number(e.target.value))}
            min={500}
            max={10000}
            step={500}
            className="w-32 rounded border border-neutral-600 bg-neutral-800 px-2 py-1.5 text-xs text-neutral-200 outline-none"
          />
        </div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={defaultEditMode}
            onChange={(e) => setDefaultEditMode(e.target.checked)}
            className="accent-[var(--color-accent)]"
          />
          <span className="text-xs text-neutral-400">Start in edit mode by default</span>
        </label>
      </div>
    </div>
  );
}
