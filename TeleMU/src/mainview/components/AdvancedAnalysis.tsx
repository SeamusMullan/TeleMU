import React, { useState, useCallback } from "react";
import { useApp } from "../store/AppContext";
import { rpcRequest } from "../hooks/useRPC";
import { SignalTree, type SelectedSignals } from "./SignalTree";
import { PlotContainer } from "./PlotContainer";
import { PLOT_COLORS } from "../lib/theme";
import { toFloat } from "../lib/filters";
import {
  gradient,
  rfft,
  rfftFreq,
  hanningWindow,
  hammingWindow,
  blackmanWindow,
  movingAverage,
  rollingStdDev,
  maxFilter1d,
  minFilter1d,
  medianFilter,
  median,
  diff,
} from "../lib/analysis";

const ANALYSIS_TYPES = [
  "Derived Signal",
  "Lap Comparison",
  "FFT / Spectral",
  "Rolling Statistics",
] as const;
type AnalysisType = (typeof ANALYSIS_TYPES)[number];

const ROLLING_STATS = [
  "Moving Average",
  "Rolling Std Dev",
  "Upper Envelope",
  "Lower Envelope",
  "Median Filter",
] as const;

const FFT_WINDOWS = ["None", "Hanning", "Hamming", "Blackman"] as const;
const DERIVED_OPS = ["+", "-", "*", "/", "d/dt"] as const;

export function AdvancedAnalysis() {
  const { state } = useApp();
  const [analysisType, setAnalysisType] = useState<AnalysisType>("Derived Signal");
  const [signals, setSignals] = useState<SelectedSignals>({});
  const [xAxis, setXAxis] = useState<"ts" | "(row index)">("ts");

  // Derived signal state
  const [derivedA, setDerivedA] = useState("");
  const [derivedB, setDerivedB] = useState("");
  const [derivedOp, setDerivedOp] = useState<string>("+");
  const [derivedPlotOriginal, setDerivedPlotOriginal] = useState(false);

  // Lap state
  const [lapMarkerTable, setLapMarkerTable] = useState("");
  const [lapSignalTable, setLapSignalTable] = useState("");
  const [lapEdges, setLapEdges] = useState<number[]>([]);
  const [lapNormalize, setLapNormalize] = useState(false);
  const [lapCount, setLapCount] = useState("");

  // FFT state
  const [fftWindow, setFftWindow] = useState<string>("None");
  const [fftLog, setFftLog] = useState(false);
  const [fftMaxFreq, setFftMaxFreq] = useState("");

  // Rolling state
  const [rollingWindow, setRollingWindow] = useState(50);
  const [rollingStat, setRollingStat] = useState<string>("Moving Average");
  const [rollingShowOriginal, setRollingShowOriginal] = useState(true);

  // Range filter
  const [rangeFrom, setRangeFrom] = useState("");
  const [rangeTo, setRangeTo] = useState("");

  // Plot
  const [plotData, setPlotData] = useState<Plotly.Data[]>([]);
  const [plotLayout, setPlotLayout] = useState<Partial<Plotly.Layout>>({});
  const [status, setStatus] = useState("");

  const tableNames = state.tables.map((t) => t.name);

  const fetchTableData = useCallback(
    async (table: string, col?: string): Promise<{ ts: number[]; vals: number[] } | null> => {
      const schema = await rpcRequest("tableSchema", { table });
      const colNames = schema.map((c) => c.name);
      let valCol = col && colNames.includes(col) ? col : null;
      if (!valCol && colNames.includes("value")) valCol = "value";
      if (!valCol) {
        const numCols = state.numericColumns[table] ?? [];
        const nonTs = numCols.filter((c) => c !== "ts");
        if (nonTs.length > 0) valCol = nonTs[0];
      }
      if (!valCol) return null;

      const fetchCols = colNames.includes("ts") ? ["ts", valCol] : [valCol];
      const result = await rpcRequest("fetchColumns", { table, columns: fetchCols });
      if (result.rows.length === 0) return null;

      if (colNames.includes("ts")) {
        return {
          ts: result.rows.map((r) => toFloat(r[0])),
          vals: result.rows.map((r) => toFloat(r[1])),
        };
      } else {
        return {
          ts: result.rows.map((_, i) => i),
          vals: result.rows.map((r) => toFloat(r[0])),
        };
      }
    },
    [state.numericColumns]
  );

  const applyRangeFilter = useCallback(
    (ts: number[], ...arrays: number[][]): [number[], ...number[][]] => {
      const from = rangeFrom.trim() ? parseFloat(rangeFrom) : null;
      const to = rangeTo.trim() ? parseFloat(rangeTo) : null;
      if (from === null && to === null) return [ts, ...arrays];

      const mask = ts.map((t) => {
        if (from !== null && t < from) return false;
        if (to !== null && t > to) return false;
        return true;
      });

      const filteredTs = ts.filter((_, i) => mask[i]);
      const filteredArrays = arrays.map((arr) => arr.filter((_, i) => mask[i]));
      return [filteredTs, ...filteredArrays];
    },
    [rangeFrom, rangeTo]
  );

  // ── Detect laps ──
  const detectLaps = useCallback(async () => {
    if (!lapMarkerTable) {
      setLapCount("No marker selected");
      return;
    }
    const result = await fetchTableData(lapMarkerTable);
    if (!result) {
      setLapCount("Could not read marker data");
      return;
    }

    let { ts, vals } = result;
    // Remove NaN
    const valid = ts.map((t, i) => !isNaN(t) && !isNaN(vals[i]));
    ts = ts.filter((_, i) => valid[i]);
    vals = vals.filter((_, i) => valid[i]);

    if (ts.length === 0) {
      setLapCount("No valid data in lap table");
      return;
    }

    // Sort by ts
    const indices = ts.map((_, i) => i).sort((a, b) => ts[a] - ts[b]);
    ts = indices.map((i) => ts[i]);
    vals = indices.map((i) => vals[i]);

    // Deduplicate by value change
    const keep = [0];
    for (let i = 1; i < vals.length; i++) {
      if (vals[i] !== vals[keep[keep.length - 1]]) keep.push(i);
    }
    const edges = keep.map((i) => ts[i]);
    setLapEdges(edges);
    const nLaps = Math.max(0, edges.length - 1);
    setLapCount(`${nLaps} laps detected (${edges.length} boundaries)`);
  }, [lapMarkerTable, fetchTableData]);

  // ── Analyze dispatch ──
  const handleAnalyze = useCallback(async () => {
    try {
      if (analysisType === "Derived Signal") await analyzeDerived();
      else if (analysisType === "Lap Comparison") await analyzeLapComparison();
      else if (analysisType === "FFT / Spectral") await analyzeFFT();
      else if (analysisType === "Rolling Statistics") await analyzeRolling();
    } catch (err) {
      setStatus(`Error: ${err instanceof Error ? err.message : String(err)}`);
    }
  }, [analysisType, signals, derivedA, derivedB, derivedOp, derivedPlotOriginal,
      lapEdges, lapSignalTable, lapNormalize, fftWindow, fftLog, fftMaxFreq,
      rollingWindow, rollingStat, rollingShowOriginal, xAxis, rangeFrom, rangeTo]);

  // ── Derived Signal ──
  const analyzeDerived = async () => {
    if (!derivedA) { setStatus("Select Signal A"); return; }
    const resultA = await fetchTableData(derivedA);
    if (!resultA) { setStatus(`Could not read data from ${derivedA}`); return; }

    const traces: Plotly.Data[] = [];
    let title = "";

    if (derivedOp === "d/dt") {
      let [ts, vals] = applyRangeFilter(resultA.ts, resultA.vals);
      const dVals = gradient(vals);
      const dTs = gradient(ts);
      const derivative = dVals.map((dv, i) => {
        const dt = dTs[i];
        const r = dt !== 0 ? dv / dt : NaN;
        return isFinite(r) ? r : NaN;
      });

      if (derivedPlotOriginal) {
        traces.push({
          x: ts, y: vals, type: "scatter", mode: "lines",
          name: derivedA, line: { color: PLOT_COLORS[0], width: 1 }, opacity: 0.5,
        });
        traces.push({
          x: ts, y: derivative, type: "scatter", mode: "lines",
          name: `d/dt(${derivedA})`, line: { color: PLOT_COLORS[1], width: 1 }, yaxis: "y2",
        });
      } else {
        traces.push({
          x: ts, y: derivative, type: "scatter", mode: "lines",
          name: `d/dt(${derivedA})`, line: { color: PLOT_COLORS[1], width: 1 },
        });
      }
      title = `Derivative of ${derivedA}`;
      setStatus(`d/dt(${derivedA}): ${ts.length} points`);
    } else {
      if (!derivedB) { setStatus("Select Signal B"); return; }
      const resultB = await fetchTableData(derivedB);
      if (!resultB) { setStatus(`Could not read data from ${derivedB}`); return; }

      const n = Math.min(resultA.ts.length, resultB.ts.length);
      let ts = resultA.ts.slice(0, n);
      let a = resultA.vals.slice(0, n);
      let b = resultB.vals.slice(0, n);
      [ts, a, b] = applyRangeFilter(ts, a, b);

      let derived: number[];
      if (derivedOp === "+") derived = a.map((v, i) => v + b[i]);
      else if (derivedOp === "-") derived = a.map((v, i) => v - b[i]);
      else if (derivedOp === "*") derived = a.map((v, i) => v * b[i]);
      else if (derivedOp === "/") derived = a.map((v, i) => b[i] !== 0 ? v / b[i] : NaN);
      else derived = a;

      if (derivedPlotOriginal) {
        traces.push({
          x: ts, y: a, type: "scatter", mode: "lines",
          name: derivedA, line: { color: PLOT_COLORS[0], width: 1 }, opacity: 0.5,
        });
        traces.push({
          x: ts, y: b, type: "scatter", mode: "lines",
          name: derivedB, line: { color: PLOT_COLORS[1], width: 1 }, opacity: 0.5,
        });
      }
      traces.push({
        x: ts, y: derived, type: "scatter", mode: "lines",
        name: `${derivedA} ${derivedOp} ${derivedB}`, line: { color: PLOT_COLORS[2], width: 1 },
      });
      title = `${derivedA} ${derivedOp} ${derivedB}`;
      setStatus(`${title}: ${ts.length} points`);
    }

    setPlotData(traces);
    const layout: Partial<Plotly.Layout> = { title: { text: title }, xaxis: { title: { text: "ts" } } };
    if (derivedOp === "d/dt" && derivedPlotOriginal) {
      layout.yaxis2 = {
        title: { text: `d/dt(${derivedA})` },
        overlaying: "y",
        side: "right",
        gridcolor: "#3a3a3a",
      } as any;
    }
    setPlotLayout(layout);
  };

  // ── Lap Comparison ──
  const analyzeLapComparison = async () => {
    if (lapEdges.length < 2) {
      setStatus("Detect laps first (need at least 2 markers)");
      return;
    }
    if (!lapSignalTable) {
      setStatus("Select a signal to compare");
      return;
    }
    const result = await fetchTableData(lapSignalTable);
    if (!result) { setStatus(`Could not read data from ${lapSignalTable}`); return; }

    const { ts, vals } = result;
    const traces: Plotly.Data[] = [];

    for (let i = 0; i < lapEdges.length - 1; i++) {
      const tStart = lapEdges[i];
      const tEnd = lapEdges[i + 1];
      const mask = ts.map((t) => t >= tStart && t < tEnd);
      const lapTs = ts.filter((_, j) => mask[j]);
      const lapVals = vals.filter((_, j) => mask[j]);

      if (lapTs.length < 2) continue;
      const lapDuration = lapTs[lapTs.length - 1] - lapTs[0];
      const x = lapNormalize && lapDuration > 0
        ? lapTs.map((t) => (t - lapTs[0]) / lapDuration)
        : lapTs.map((t) => t - lapTs[0]);

      traces.push({
        x,
        y: lapVals,
        type: "scatter",
        mode: "lines",
        name: `Lap ${i + 1} (${lapDuration.toFixed(1)}s)`,
        line: { color: PLOT_COLORS[i % PLOT_COLORS.length], width: 1 },
      });
    }

    setPlotData(traces);
    setPlotLayout({
      title: { text: `Lap Comparison — ${lapSignalTable}` },
      xaxis: { title: { text: lapNormalize ? "Normalized time (0-1)" : "Time from lap start (s)" } },
      yaxis: { title: { text: lapSignalTable } },
    });
    setStatus(`${lapEdges.length - 1} laps overlaid for ${lapSignalTable}`);
  };

  // ── FFT / Spectral ──
  const analyzeFFT = async () => {
    const allSignals = Object.entries(signals);
    const total = allSignals.reduce((s, [_, c]) => s + c.length, 0);
    if (total !== 1) {
      setStatus("Select exactly 1 signal for FFT");
      return;
    }
    const table = allSignals[0][0];
    const result = await fetchTableData(table);
    if (!result) { setStatus(`Could not read data from ${table}`); return; }

    let [ts, vals] = applyRangeFilter(result.ts, result.vals);

    // Remove NaN
    const valid = ts.map((t, i) => !isNaN(t) && !isNaN(vals[i]));
    ts = ts.filter((_, i) => valid[i]);
    vals = vals.filter((_, i) => valid[i]);

    if (vals.length < 4) { setStatus("Not enough data for FFT"); return; }

    // Sample rate
    const dts = diff(ts);
    const dt = median(dts);
    if (dt <= 0) { setStatus("Cannot estimate sample rate (non-monotonic ts)"); return; }
    const fs = 1.0 / dt;

    // Subtract mean
    const mean = vals.reduce((s, v) => s + v, 0) / vals.length;
    vals = vals.map((v) => v - mean);

    // Apply window
    let w: number[];
    if (fftWindow === "Hanning") w = hanningWindow(vals.length);
    else if (fftWindow === "Hamming") w = hammingWindow(vals.length);
    else if (fftWindow === "Blackman") w = blackmanWindow(vals.length);
    else w = vals.map(() => 1);
    vals = vals.map((v, i) => v * w[i]);

    // FFT
    const { re, im } = rfft(vals);
    let xf = rfftFreq(vals.length, dt);
    let magnitude = re.map((r, i) => (Math.sqrt(r * r + im[i] * im[i]) / vals.length) * 2);

    // Max frequency
    const maxFreqVal = fftMaxFreq.trim() ? parseFloat(fftMaxFreq) : null;
    if (maxFreqVal !== null && !isNaN(maxFreqVal)) {
      const mask = xf.map((f) => f <= maxFreqVal);
      xf = xf.filter((_, i) => mask[i]);
      magnitude = magnitude.filter((_, i) => mask[i]);
    }

    // Log scale
    let ylabel: string;
    if (fftLog) {
      magnitude = magnitude.map((m) => 20 * Math.log10(m + 1e-12));
      ylabel = "Magnitude (dB)";
    } else {
      ylabel = "Magnitude";
    }

    setPlotData([
      {
        x: xf,
        y: magnitude,
        type: "scatter",
        mode: "lines",
        fill: "tozeroy",
        line: { color: PLOT_COLORS[0], width: 1 },
        fillcolor: `${PLOT_COLORS[0]}66`,
        name: "FFT",
      },
    ]);
    setPlotLayout({
      title: { text: `FFT — ${table}` },
      xaxis: { title: { text: "Frequency (Hz)" } },
      yaxis: { title: { text: ylabel } },
    });
    setStatus(`FFT of ${table}: ${vals.length} samples, fs=${fs.toFixed(1)} Hz`);
  };

  // ── Rolling Statistics ──
  const analyzeRolling = async () => {
    const allSignals = Object.entries(signals);
    if (allSignals.reduce((s, [_, c]) => s + c.length, 0) === 0) {
      setStatus("Select at least one signal");
      return;
    }

    const useIndex = xAxis === "(row index)";
    const traces: Plotly.Data[] = [];
    let colorIdx = 0;

    for (const [table, cols] of allSignals) {
      for (const col of cols) {
        const result = await fetchTableData(table, col);
        if (!result) continue;

        let [ts, vals] = applyRangeFilter(result.ts, result.vals);
        if (vals.length < rollingWindow) {
          setStatus(`Not enough data for window size ${rollingWindow}`);
          continue;
        }

        const x = useIndex ? vals.map((_, i) => i) : ts;
        const label = `${table}.${col}`;

        if (rollingShowOriginal) {
          traces.push({
            x, y: vals, type: "scatter", mode: "lines",
            name: `${label} (original)`,
            line: { color: PLOT_COLORS[colorIdx % PLOT_COLORS.length], width: 1 },
            opacity: 0.3,
          });
          colorIdx++;
        }

        let resultVals: number[];
        if (rollingStat === "Moving Average") resultVals = movingAverage(vals, rollingWindow);
        else if (rollingStat === "Rolling Std Dev") resultVals = rollingStdDev(vals, rollingWindow);
        else if (rollingStat === "Upper Envelope") resultVals = maxFilter1d(vals, rollingWindow);
        else if (rollingStat === "Lower Envelope") resultVals = minFilter1d(vals, rollingWindow);
        else if (rollingStat === "Median Filter") resultVals = medianFilter(vals, rollingWindow);
        else resultVals = vals;

        traces.push({
          x, y: resultVals, type: "scatter", mode: "lines",
          name: `${label} (${rollingStat}, w=${rollingWindow})`,
          line: { color: PLOT_COLORS[colorIdx % PLOT_COLORS.length], width: 1.5 },
        });
        colorIdx++;
      }
    }

    setPlotData(traces);
    setPlotLayout({
      title: { text: `Rolling Statistics — ${rollingStat}` },
      xaxis: { title: { text: useIndex ? "Row Index" : "ts" } },
    });
    const total = allSignals.reduce((s, [_, c]) => s + c.length, 0);
    setStatus(`${rollingStat} on ${total} signal(s), window=${rollingWindow}`);
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-56 flex-shrink-0 border-r border-telemu-border p-2 flex flex-col gap-2 overflow-auto">
        <SignalTree onSelectionChange={setSignals} />

        <div className="flex items-center gap-1">
          <span className="text-xs text-telemu-text-dim">X:</span>
          <select
            value={xAxis}
            onChange={(e) => setXAxis(e.target.value as any)}
            className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text"
          >
            <option value="ts">ts</option>
            <option value="(row index)">(row index)</option>
          </select>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-xs text-telemu-text-dim">Analysis:</span>
          <select
            value={analysisType}
            onChange={(e) => setAnalysisType(e.target.value as AnalysisType)}
            className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text"
          >
            {ANALYSIS_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {/* Controls panel */}
        <div className="border border-telemu-border rounded p-2 space-y-1.5">
          <div className="text-xs font-medium text-telemu-text-dim">Controls</div>

          {analysisType === "Derived Signal" && (
            <>
              <div className="text-xs text-telemu-text-dim">Signal A:</div>
              <select value={derivedA} onChange={(e) => setDerivedA(e.target.value)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text">
                <option value="">Select...</option>
                {tableNames.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <div className="text-xs text-telemu-text-dim">Operator:</div>
              <select value={derivedOp} onChange={(e) => setDerivedOp(e.target.value)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text">
                {DERIVED_OPS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
              <div className="text-xs text-telemu-text-dim">Signal B:</div>
              <select value={derivedB} onChange={(e) => setDerivedB(e.target.value)}
                disabled={derivedOp === "d/dt"}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text disabled:opacity-40">
                <option value="">Select...</option>
                {tableNames.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <label className="flex items-center gap-1.5 text-xs text-telemu-text cursor-pointer">
                <input type="checkbox" checked={derivedPlotOriginal}
                  onChange={(e) => setDerivedPlotOriginal(e.target.checked)}
                  className="accent-telemu-accent" />
                Plot original signals too
              </label>
            </>
          )}

          {analysisType === "Lap Comparison" && (
            <>
              <div className="text-xs text-telemu-text-dim">Lap Table:</div>
              <select value={lapMarkerTable} onChange={(e) => setLapMarkerTable(e.target.value)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text">
                <option value="">Select...</option>
                {tableNames.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <button onClick={detectLaps}
                className="w-full px-2 py-1 bg-telemu-bg-lighter border border-telemu-border rounded text-xs text-telemu-text hover:bg-telemu-border hover:text-telemu-text-bright">
                Detect Laps
              </button>
              {lapCount && <div className="text-xs text-telemu-text-dim">{lapCount}</div>}
              <div className="text-xs text-telemu-text-dim">Signal to Compare:</div>
              <select value={lapSignalTable} onChange={(e) => setLapSignalTable(e.target.value)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text">
                <option value="">Select...</option>
                {tableNames.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <label className="flex items-center gap-1.5 text-xs text-telemu-text cursor-pointer">
                <input type="checkbox" checked={lapNormalize}
                  onChange={(e) => setLapNormalize(e.target.checked)}
                  className="accent-telemu-accent" />
                Normalize lap time (0-1)
              </label>
            </>
          )}

          {analysisType === "FFT / Spectral" && (
            <>
              <div className="text-xs text-telemu-text-dim">Window:</div>
              <select value={fftWindow} onChange={(e) => setFftWindow(e.target.value)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text">
                {FFT_WINDOWS.map((w) => <option key={w} value={w}>{w}</option>)}
              </select>
              <label className="flex items-center gap-1.5 text-xs text-telemu-text cursor-pointer">
                <input type="checkbox" checked={fftLog}
                  onChange={(e) => setFftLog(e.target.checked)}
                  className="accent-telemu-accent" />
                Log scale (dB)
              </label>
              <div className="text-xs text-telemu-text-dim">Max frequency (Hz):</div>
              <input type="text" placeholder="auto" value={fftMaxFreq}
                onChange={(e) => setFftMaxFreq(e.target.value)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none" />
            </>
          )}

          {analysisType === "Rolling Statistics" && (
            <>
              <div className="text-xs text-telemu-text-dim">Window size:</div>
              <input type="number" min={3} max={10000} value={rollingWindow}
                onChange={(e) => setRollingWindow(parseInt(e.target.value) || 50)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none" />
              <div className="text-xs text-telemu-text-dim">Statistic:</div>
              <select value={rollingStat} onChange={(e) => setRollingStat(e.target.value)}
                className="w-full bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text">
                {ROLLING_STATS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <label className="flex items-center gap-1.5 text-xs text-telemu-text cursor-pointer">
                <input type="checkbox" checked={rollingShowOriginal}
                  onChange={(e) => setRollingShowOriginal(e.target.checked)}
                  className="accent-telemu-accent" />
                Show original signal
              </label>
            </>
          )}
        </div>

        {/* Range filter */}
        <div className="border border-telemu-border rounded p-2 space-y-1.5">
          <div className="text-xs font-medium text-telemu-text-dim">Filters</div>
          <div className="flex items-center gap-1">
            <span className="text-xs text-telemu-text-dim w-8">From:</span>
            <input type="text" placeholder="start" value={rangeFrom}
              onChange={(e) => setRangeFrom(e.target.value)}
              className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none" />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-xs text-telemu-text-dim w-8">To:</span>
            <input type="text" placeholder="end" value={rangeTo}
              onChange={(e) => setRangeTo(e.target.value)}
              className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none" />
          </div>
        </div>

        <button onClick={handleAnalyze}
          className="w-full px-3 py-1.5 bg-telemu-accent text-telemu-text-bright rounded text-sm font-medium hover:bg-telemu-accent-hover active:bg-telemu-accent-pressed">
          Analyze
        </button>

        {status && (
          <div className="text-xs text-telemu-text-dim break-words">{status}</div>
        )}
      </div>

      {/* Plot area */}
      <div className="flex-1 overflow-hidden">
        {plotData.length > 0 ? (
          <PlotContainer data={plotData} layout={plotLayout} />
        ) : (
          <div className="flex items-center justify-center h-full text-telemu-text-dim text-sm">
            Configure analysis and click Analyze
          </div>
        )}
      </div>
    </div>
  );
}

import type Plotly from "plotly.js";
