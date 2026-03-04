/** Recording controls — start/stop button, timer, file-size, data-rate, output dir. */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/rest";
import { useRecordingStore } from "../../stores/recordingStore";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatRate(bps: number): string {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${(bps / (1024 * 1024)).toFixed(2)} MB/s`;
}

export default function RecordingControls() {
  const { active, filename, duration_seconds, file_size_bytes, data_rate_bps, outputDir, setStatus, setOutputDir } =
    useRecordingStore();

  const [showDirInput, setShowDirInput] = useState(false);
  const [dirDraft, setDirDraft] = useState(outputDir);
  const [confirmStop, setConfirmStop] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleStart = useCallback(async () => {
    setError(null);
    try {
      const s = await api.startRecording(outputDir ? { output_dir: outputDir } : {});
      setStatus(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start recording");
    }
  }, [outputDir, setStatus]);

  const handleStop = useCallback(async () => {
    setConfirmStop(false);
    setError(null);
    try {
      const s = await api.stopRecording();
      setStatus(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop recording");
    }
  }, [setStatus]);

  // Poll status while recording
  useEffect(() => {
    if (active) {
      pollRef.current = setInterval(async () => {
        try {
          const s = await api.recordingStatus();
          setStatus(s);
        } catch {
          // silently ignore transient errors
        }
      }, 1000);
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [active, setStatus]);

  // Ctrl+R keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "r") {
        e.preventDefault();
        if (active) {
          setConfirmStop(true);
        } else {
          handleStart();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [active, handleStart]);

  const handleToggle = () => {
    if (active) {
      setConfirmStop(true);
    } else {
      handleStart();
    }
  };

  const handleDirSave = () => {
    setOutputDir(dirDraft);
    setShowDirInput(false);
  };

  return (
    <div className="rounded border border-neutral-700 bg-neutral-900 p-3">
      {/* Header row */}
      <div className="mb-2 flex items-center gap-3">
        {/* Record toggle button */}
        <button
          onClick={handleToggle}
          title={active ? "Stop recording (Ctrl+R)" : "Start recording (Ctrl+R)"}
          className="flex items-center gap-2 rounded px-3 py-1 text-xs font-bold transition-colors"
          style={{
            backgroundColor: active ? "var(--color-red, #ef4444)" : "#2a2a2a",
            color: active ? "#fff" : "#aaa",
          }}
        >
          {/* Red dot indicator when active */}
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{
              backgroundColor: active ? "#fff" : "var(--color-red, #ef4444)",
              animation: active ? "pulse 1s infinite" : "none",
            }}
          />
          {active ? "Stop" : "Record"}
        </button>

        {/* Duration timer */}
        {active && (
          <span className="font-mono text-xs text-neutral-300">
            {formatDuration(duration_seconds)}
          </span>
        )}

        {/* File size */}
        {active && (
          <span className="text-xs text-neutral-400">{formatBytes(file_size_bytes)}</span>
        )}

        {/* Data rate */}
        {active && (
          <span className="text-xs text-neutral-500">{formatRate(data_rate_bps)}</span>
        )}

        {/* Output directory toggle */}
        <button
          onClick={() => {
            setDirDraft(outputDir);
            setShowDirInput((v) => !v);
          }}
          title="Set output directory"
          className="ml-auto text-xs text-neutral-500 hover:text-neutral-300"
        >
          ⚙ dir
        </button>
      </div>

      {/* Filename when active */}
      {active && filename && (
        <div className="mb-1 truncate text-xs text-neutral-500" title={filename}>
          {filename}
        </div>
      )}

      {/* Output directory input */}
      {showDirInput && (
        <div className="mt-2 flex gap-2">
          <input
            type="text"
            value={dirDraft}
            onChange={(e) => setDirDraft(e.target.value)}
            placeholder="Output directory (leave blank for default)"
            className="flex-1 rounded border border-neutral-600 bg-neutral-800 px-2 py-1 text-xs text-neutral-200 outline-none"
          />
          <button
            onClick={handleDirSave}
            className="rounded bg-neutral-700 px-2 py-1 text-xs text-neutral-200 hover:bg-neutral-600"
          >
            Save
          </button>
        </div>
      )}

      {/* Error display */}
      {error && <div className="mt-1 text-xs text-red-400">{error}</div>}

      {/* Stop confirmation dialog */}
      {confirmStop && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="rounded-lg border border-neutral-700 bg-neutral-900 p-6 shadow-xl">
            <p className="mb-4 text-sm text-neutral-200">
              Stop recording and save the file?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmStop(false)}
                className="rounded bg-neutral-700 px-4 py-2 text-xs text-neutral-200 hover:bg-neutral-600"
              >
                Cancel
              </button>
              <button
                onClick={handleStop}
                className="rounded px-4 py-2 text-xs font-bold text-white"
                style={{ backgroundColor: "var(--color-red, #ef4444)" }}
              >
                Stop &amp; Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
