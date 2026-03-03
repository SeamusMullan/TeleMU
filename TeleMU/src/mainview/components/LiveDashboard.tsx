import React, { useState, useEffect, useCallback, useRef } from "react";
import { rpcRequest } from "../hooks/useRPC";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, "0")}:${m
    .toString()
    .padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatRate(bytesPerSec: number): string {
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`;
  if (bytesPerSec < 1024 * 1024)
    return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
  return `${(bytesPerSec / (1024 * 1024)).toFixed(2)} MB/s`;
}

export function LiveDashboard() {
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [fileSize, setFileSize] = useState(0);
  const [dataRate, setDataRate] = useState(0);
  const [recordingPath, setRecordingPath] = useState<string | null>(null);
  const [outputDir, setOutputDir] = useState("");
  const [customFilename, setCustomFilename] = useState("");
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const prevSizeRef = useRef<number>(0);

  // Poll recording status when active
  useEffect(() => {
    if (!recording) return;

    const interval = setInterval(async () => {
      try {
        const status = await rpcRequest("getRecordingStatus");
        if (status.recording) {
          const elapsed = (Date.now() - startTimeRef.current) / 1000;
          setDuration(elapsed);

          const sizeDelta = status.size - prevSizeRef.current;
          setDataRate(sizeDelta); // per second (1s interval)
          prevSizeRef.current = status.size;
          setFileSize(status.size);
        }
      } catch {
        // Status polling failed, ignore
      }
    }, 1000);

    timerRef.current = interval;
    return () => clearInterval(interval);
  }, [recording]);

  const handleStart = useCallback(async () => {
    setError(null);
    try {
      const result = await rpcRequest("startRecording", {
        outputDir: outputDir || undefined,
        filename: customFilename.trim() || undefined,
      });
      setRecordingPath(result.path);
      setRecording(true);
      setDuration(0);
      setFileSize(0);
      setDataRate(0);
      startTimeRef.current = Date.now();
      prevSizeRef.current = 0;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start recording");
    }
  }, [outputDir, customFilename]);

  const handleStop = useCallback(async () => {
    setError(null);
    try {
      const result = await rpcRequest("stopRecording");
      setRecording(false);
      setShowStopConfirm(false);
      setDuration(result.duration);
      setFileSize(result.size);
      setDataRate(0);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop recording");
    }
  }, []);

  const handleToggle = useCallback(() => {
    if (recording) {
      setShowStopConfirm(true);
    } else {
      handleStart();
    }
  }, [recording, handleStart]);

  const handleBrowseDir = useCallback(async () => {
    try {
      const path = await rpcRequest("openFileDialog");
      if (path) {
        const lastSep = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
        const dir = lastSep >= 0 ? path.substring(0, lastSep) : path;
        setOutputDir(dir);
      }
    } catch {
      // Dialog cancelled
    }
  }, []);

  // Keyboard shortcut: Ctrl+R to toggle recording
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "r") {
        e.preventDefault();
        handleToggle();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleToggle]);

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <h2 className="text-lg font-bold text-telemu-accent">Live Dashboard</h2>

      {/* Recording Controls */}
      <div className="bg-telemu-bg-light border border-telemu-border rounded-lg p-4">
        <div className="flex items-center gap-4">
          {/* Record button */}
          <button
            onClick={handleToggle}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-colors ${
              recording
                ? "bg-red-700 hover:bg-red-800 text-white"
                : "bg-telemu-accent hover:bg-telemu-accent-hover text-telemu-text-bright"
            }`}
            title={`${recording ? "Stop" : "Start"} Recording (Ctrl+R)`}
          >
            {/* Red dot indicator */}
            <span
              className={`inline-block w-3 h-3 rounded-full ${
                recording ? "bg-red-400 animate-pulse" : "bg-red-600"
              }`}
            />
            {recording ? "Stop Recording" : "Start Recording"}
          </button>

          {/* Duration */}
          <div className="flex flex-col items-center">
            <span className="text-xs text-telemu-text-dim">Duration</span>
            <span className="text-lg font-mono text-telemu-text">
              {formatDuration(duration)}
            </span>
          </div>

          {/* File Size */}
          <div className="flex flex-col items-center">
            <span className="text-xs text-telemu-text-dim">File Size</span>
            <span className="text-lg font-mono text-telemu-text">
              {formatSize(fileSize)}
            </span>
          </div>

          {/* Data Rate */}
          <div className="flex flex-col items-center">
            <span className="text-xs text-telemu-text-dim">Data Rate</span>
            <span className="text-lg font-mono text-telemu-text">
              {formatRate(dataRate)}
            </span>
          </div>
        </div>

        {/* Recording path indicator */}
        {recordingPath && (
          <div className="mt-3 text-xs text-telemu-text-dim truncate">
            <span className="font-medium">File:</span> {recordingPath}
          </div>
        )}

        {/* Keyboard shortcut hint */}
        <div className="mt-2 text-xs text-telemu-text-dim">
          Press <kbd className="px-1 py-0.5 bg-telemu-bg border border-telemu-border rounded text-telemu-text text-[10px]">Ctrl+R</kbd> to toggle recording
        </div>
      </div>

      {/* Output Settings */}
      <div className="bg-telemu-bg-light border border-telemu-border rounded-lg p-4">
        <h3 className="text-sm font-medium text-telemu-text mb-3">
          Output Settings
        </h3>

        {/* Output directory */}
        <div className="flex items-center gap-2 mb-3">
          <label className="text-xs text-telemu-text-dim w-24 flex-shrink-0">
            Output Directory
          </label>
          <input
            type="text"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            disabled={recording}
            className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-2 py-1 text-xs text-telemu-text focus:border-telemu-accent outline-none disabled:opacity-50"
            placeholder="~/recordings"
          />
          <button
            onClick={handleBrowseDir}
            disabled={recording}
            className="px-3 py-1 rounded text-xs text-telemu-text hover:bg-telemu-bg-lighter hover:text-telemu-accent border border-telemu-border disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Browse
          </button>
        </div>

        {/* Custom filename */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-telemu-text-dim w-24 flex-shrink-0">
            Filename
          </label>
          <input
            type="text"
            value={customFilename}
            onChange={(e) => setCustomFilename(e.target.value)}
            disabled={recording}
            className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-2 py-1 text-xs text-telemu-text focus:border-telemu-accent outline-none disabled:opacity-50"
            placeholder="Auto: track_car_YYYY_MM_DDTHH_MM_SSZ.duckdb"
          />
        </div>
        <p className="text-[10px] text-telemu-text-dim mt-1 ml-[104px]">
          Leave blank to auto-generate (e.g. track_car_2026_03_03T18_30_00Z.duckdb)
        </p>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Stop confirmation dialog */}
      {showStopConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-telemu-bg-light border border-telemu-border rounded-lg p-6 max-w-sm mx-4 shadow-xl">
            <h3 className="text-sm font-bold text-telemu-text mb-2">
              Stop Recording?
            </h3>
            <p className="text-xs text-telemu-text-dim mb-4">
              Are you sure you want to stop recording? The current session has
              been running for{" "}
              <span className="text-telemu-text font-mono">
                {formatDuration(duration)}
              </span>{" "}
              with{" "}
              <span className="text-telemu-text font-mono">
                {formatSize(fileSize)}
              </span>{" "}
              of data captured.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowStopConfirm(false)}
                className="px-4 py-1.5 rounded text-xs text-telemu-text hover:bg-telemu-bg-lighter border border-telemu-border"
              >
                Cancel
              </button>
              <button
                onClick={handleStop}
                className="px-4 py-1.5 rounded text-xs bg-red-700 hover:bg-red-800 text-white font-medium"
              >
                Stop Recording
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
