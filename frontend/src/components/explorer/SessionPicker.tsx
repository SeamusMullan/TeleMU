/** Session picker — dropdown to select and open .duckdb session files. */

import { useEffect } from "react";
import { useSessionStore } from "../../stores/sessionStore";

export default function SessionPicker() {
  const { sessions, activeSession, loading, error, fetchSessions, openSession } = useSessionStore();

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return (
    <div className="flex h-full flex-col p-3">
      <div className="mb-2 text-xs font-bold text-neutral-300">Session</div>
      <select
        value={activeSession ?? ""}
        onChange={(e) => {
          if (e.target.value) openSession(e.target.value);
        }}
        disabled={loading}
        className="w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-1.5 text-xs text-neutral-200 outline-none"
      >
        <option value="">Select a session...</option>
        {sessions.map((s) => (
          <option key={s.filename} value={s.filename}>
            {s.filename} ({(s.size_bytes / 1024 / 1024).toFixed(1)} MB)
          </option>
        ))}
      </select>
      {loading && <div className="mt-1 text-xs text-neutral-500">Loading...</div>}
      {error && <div className="mt-1 text-xs text-red-400">{error}</div>}
      {activeSession && (
        <div className="mt-2 text-xs text-neutral-500">
          Active: <span className="text-neutral-300">{activeSession}</span>
        </div>
      )}
    </div>
  );
}
