/** Convert .tmu recordings to DuckDB — file selection, batch, progress, auto-open. */

import { useEffect, useState } from "react";
import { api } from "../api/rest";
import type { TmuFileInfo, ConvertFileResult } from "../api/types";
import { useSessionStore } from "../stores/sessionStore";

export default function ConvertPage() {
  const [tmuFiles, setTmuFiles] = useState<TmuFileInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [autoOpen, setAutoOpen] = useState(false);
  const [converting, setConverting] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const [results, setResults] = useState<ConvertFileResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const openSession = useSessionStore((s) => s.openSession);

  useEffect(() => {
    api
      .tmuFiles()
      .then(setTmuFiles)
      .catch((err) => setError(String(err)));
  }, []);

  const toggleFile = (filename: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(filename)) next.delete(filename);
      else next.add(filename);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === tmuFiles.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(tmuFiles.map((f) => f.filename)));
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleConvert = async () => {
    if (selected.size === 0) return;

    setConverting(true);
    setProgress(0);
    setResults(null);
    setError(null);

    try {
      // Simulate progress since the API call is synchronous
      const progressInterval = setInterval(() => {
        setProgress((p) => Math.min(p + 5, 90));
      }, 200);

      const resp = await api.convert({
        files: Array.from(selected),
        auto_open: autoOpen,
      });

      clearInterval(progressInterval);
      setProgress(100);
      setResults(resp.results);

      // Auto-open first successful result if enabled
      if (autoOpen) {
        const first = resp.results.find((r) => r.success);
        if (first?.output) {
          openSession(first.output);
        }
      }

      // Refresh the file list
      api.tmuFiles().then(setTmuFiles).catch(console.error);
    } catch (err) {
      setError(String(err));
    } finally {
      setConverting(false);
    }
  };

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-bold">Convert .tmu to DuckDB</h1>
      <p className="mb-4 text-sm text-neutral-500">
        Select .tmu recording files to convert to DuckDB format for analysis.
      </p>

      {error && (
        <div className="mb-4 rounded bg-red-900/50 px-3 py-2 text-sm text-red-300">{error}</div>
      )}

      {/* File list */}
      <div className="mb-4 max-w-2xl rounded-lg bg-neutral-900 p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-bold text-neutral-300">Available .tmu Files</h2>
          {tmuFiles.length > 0 && (
            <button
              onClick={selectAll}
              className="text-xs text-[var(--color-accent)] hover:underline"
            >
              {selected.size === tmuFiles.length ? "Deselect All" : "Select All"}
            </button>
          )}
        </div>

        {tmuFiles.length === 0 ? (
          <p className="text-sm text-neutral-500">
            No .tmu files found in the data directory.
          </p>
        ) : (
          <div className="max-h-64 space-y-1 overflow-y-auto">
            {tmuFiles.map((file) => (
              <label
                key={file.filename}
                className="flex cursor-pointer items-center gap-3 rounded px-2 py-1.5 hover:bg-neutral-800"
              >
                <input
                  type="checkbox"
                  checked={selected.has(file.filename)}
                  onChange={() => toggleFile(file.filename)}
                  className="accent-[var(--color-accent)]"
                />
                <span className="flex-1 font-mono text-sm text-neutral-300">{file.filename}</span>
                <span className="text-xs text-neutral-500">{formatSize(file.size_bytes)}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Options */}
      <div className="mb-4 max-w-2xl rounded-lg bg-neutral-900 p-4">
        <h2 className="mb-2 text-sm font-bold text-neutral-300">Options</h2>
        <label className="flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            checked={autoOpen}
            onChange={(e) => setAutoOpen(e.target.checked)}
            className="accent-[var(--color-accent)]"
          />
          <span className="text-sm text-neutral-400">
            Auto-open converted file in Explorer after conversion
          </span>
        </label>
      </div>

      {/* Convert button */}
      <div className="mb-4 max-w-2xl">
        <button
          onClick={handleConvert}
          disabled={selected.size === 0 || converting}
          className="rounded bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {converting
            ? "Converting..."
            : `Convert ${selected.size} file${selected.size !== 1 ? "s" : ""}`}
        </button>
      </div>

      {/* Progress bar */}
      {converting && (
        <div className="mb-4 max-w-2xl">
          <div className="h-2 overflow-hidden rounded-full bg-neutral-800">
            <div
              className="h-full rounded-full bg-[var(--color-accent)] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-neutral-500">Converting... {progress}%</p>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="max-w-2xl rounded-lg bg-neutral-900 p-4">
          <h2 className="mb-2 text-sm font-bold text-neutral-300">Results</h2>
          <div className="space-y-1">
            {results.map((r) => (
              <div
                key={r.filename}
                className="flex items-center gap-2 font-mono text-sm"
              >
                <span
                  className={r.success ? "text-green-400" : "text-red-400"}
                >
                  {r.success ? "✓" : "✗"}
                </span>
                <span className="text-neutral-300">{r.filename}</span>
                {r.success && (
                  <span className="text-neutral-500">→ {r.output}</span>
                )}
                {r.error && (
                  <span className="text-red-400">{r.error}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
