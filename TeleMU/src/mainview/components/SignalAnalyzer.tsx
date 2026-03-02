import React, { useState, useCallback } from "react";
import { useApp } from "../store/AppContext";
import { rpcRequest } from "../hooks/useRPC";
import { SignalTree, type SelectedSignals } from "./SignalTree";
import { FilterGroup } from "./FilterGroup";
import { PlotContainer } from "./PlotContainer";
import { PLOT_COLORS } from "../lib/theme";
import { DEFAULT_FILTERS, applyFilters, toFloat, type FilterState } from "../lib/filters";
import { pearsonR, spearmanR, crossCorrelate, normalize01 } from "../lib/analysis";

const PLOT_TYPES = [
  "Line",
  "Scatter",
  "Histogram",
  "Correlation Matrix",
  "Cross-Correlation",
  "Correlation Finder",
] as const;

type PlotType = (typeof PLOT_TYPES)[number];

export function SignalAnalyzer() {
  const { state } = useApp();
  const [signals, setSignals] = useState<SelectedSignals>({});
  const [xAxis, setXAxis] = useState<"ts" | "(row index)">("ts");
  const [plotType, setPlotType] = useState<PlotType>("Line");
  const [normalizeChecked, setNormalize] = useState(false);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [plotData, setPlotData] = useState<Plotly.Data[]>([]);
  const [plotLayout, setPlotLayout] = useState<Partial<Plotly.Layout>>({});
  const [status, setStatus] = useState("");

  const handlePlot = useCallback(async () => {
    if (plotType === "Correlation Finder") {
      await plotCorrelationFinder();
      return;
    }

    const signalKeys = Object.entries(signals);
    if (signalKeys.length === 0) {
      setStatus("Select at least one signal");
      return;
    }

    try {
      // Fetch data
      const tables = Object.keys(signals);
      const useIndex = xAxis === "(row index)";

      let colNames: string[] = [];
      let rows: unknown[][] = [];

      if (tables.length === 1) {
        const tbl = tables[0];
        let cols = [...signals[tbl]];
        const hasTs = state.tablesWithTs.has(tbl);
        if (!useIndex && hasTs && !cols.includes("ts")) {
          cols = ["ts", ...cols];
        }
        const result = await rpcRequest("fetchColumns", { table: tbl, columns: cols });
        colNames = result.columns.map((c) => `${tbl}.${c}`);
        rows = result.rows;
      } else {
        // Multi-table: try join on ts
        const tsTableSignals: Record<string, string[]> = {};
        for (const [tbl, cols] of Object.entries(signals)) {
          if (state.tablesWithTs.has(tbl)) {
            tsTableSignals[tbl] = cols;
          }
        }

        if (!useIndex && Object.keys(tsTableSignals).length >= 2) {
          const result = await rpcRequest("fetchJoinedColumns", {
            tableColumns: tsTableSignals,
            on: "ts",
          });
          colNames = result.columns;
          rows = result.rows;
        } else {
          // Row-aligned fetch
          let allColNames: string[] = [];
          let allColumns: number[][] = [];
          let minRows = Infinity;

          for (const [tbl, cols] of Object.entries(signals)) {
            const fetchCols = state.tablesWithTs.has(tbl) && !useIndex
              ? ["ts", ...cols.filter((c) => c !== "ts")]
              : cols;
            const result = await rpcRequest("fetchColumns", { table: tbl, columns: fetchCols });
            if (result.rows.length === 0) continue;
            minRows = Math.min(minRows, result.rows.length);
            for (let i = 0; i < result.columns.length; i++) {
              allColNames.push(`${tbl}.${result.columns[i]}`);
              allColumns.push(result.rows.map((r) => r[i] as number));
            }
          }

          if (allColumns.length > 0 && minRows < Infinity) {
            colNames = allColNames;
            rows = Array.from({ length: minRows }, (_, r) =>
              allColumns.map((col) => col[r])
            );
          }
        }
      }

      if (rows.length === 0) {
        setStatus("No data returned");
        return;
      }

      // Build numeric arrays
      const colIdx: Record<string, number> = {};
      colNames.forEach((c, i) => (colIdx[c] = i));

      // Find x key
      let xKey: string | null = null;
      if (!useIndex) {
        for (const c of colNames) {
          if (c === "ts" || c.endsWith(".ts")) {
            xKey = c;
            break;
          }
        }
      }

      // Build y arrays
      const yArrays: Record<string, number[]> = {};
      for (const c of colNames) {
        if (c === xKey) continue;
        yArrays[c] = rows.map((r) => toFloat(r[colIdx[c]]));
      }

      const xRaw = xKey
        ? rows.map((r) => toFloat(r[colIdx[xKey!]]))
        : null;

      // Apply filters
      const filtered = applyFilters(xRaw, yArrays, filters);
      if (filtered.x.length === 0) {
        setStatus("All data excluded by filters");
        return;
      }

      // Normalize if requested
      const yFinal: Record<string, number[]> = {};
      for (const [name, arr] of Object.entries(filtered.yArrays)) {
        yFinal[name] = normalizeChecked ? normalize01(arr) : arr;
      }

      // Plot
      const xLabel = xKey ? "ts" : "Row Index";
      const keys = Object.keys(yFinal);

      if (plotType === "Cross-Correlation") {
        if (keys.length !== 2) {
          setStatus("Select exactly 2 signals for Cross-Correlation");
          setPlotData([]);
          return;
        }
        plotCrossCorrelation(yFinal[keys[0]], yFinal[keys[1]], keys[0], keys[1]);
      } else if (plotType === "Correlation Matrix") {
        plotCorrelationMatrix(yFinal);
      } else if (plotType === "Histogram") {
        plotHistogram(yFinal);
      } else if (plotType === "Scatter") {
        plotScatter(filtered.x, xLabel, yFinal);
      } else {
        plotLine(filtered.x, xLabel, yFinal);
      }

      setStatus(
        `Plotted ${keys.length} signals (${filtered.x.length} points, ${filtered.excluded} excluded)`
      );
    } catch (err) {
      setStatus(`Error: ${err instanceof Error ? err.message : String(err)}`);
    }
  }, [signals, xAxis, plotType, normalizeChecked, filters, state]);

  // ── Plot methods ──

  const plotLine = (x: number[], xLabel: string, yArrays: Record<string, number[]>) => {
    const keys = Object.keys(yArrays);

    // Dual y-axis when 2 signals with >10x range ratio
    let useDualY = false;
    if (keys.length === 2) {
      const range0 = Math.max(...yArrays[keys[0]].filter((v) => !isNaN(v))) - Math.min(...yArrays[keys[0]].filter((v) => !isNaN(v)));
      const range1 = Math.max(...yArrays[keys[1]].filter((v) => !isNaN(v))) - Math.min(...yArrays[keys[1]].filter((v) => !isNaN(v)));
      if (range0 > 0 && range1 > 0) {
        useDualY = Math.max(range0, range1) / Math.min(range0, range1) > 10;
      }
    }

    const traces: Plotly.Data[] = keys.map((name, i) => ({
      x,
      y: yArrays[name],
      type: "scatter" as const,
      mode: "lines" as const,
      name,
      line: { color: PLOT_COLORS[i % PLOT_COLORS.length], width: 1 },
      yaxis: useDualY && i === 1 ? "y2" : "y",
    }));

    const layout: Partial<Plotly.Layout> = {
      xaxis: { title: { text: xLabel } },
    };
    if (useDualY) {
      layout.yaxis = { title: { text: keys[0] }, titlefont: { color: PLOT_COLORS[0] } } as any;
      layout.yaxis2 = {
        title: { text: keys[1] },
        titlefont: { color: PLOT_COLORS[1] },
        overlaying: "y",
        side: "right",
        gridcolor: "#3a3a3a",
      } as any;
    }

    setPlotData(traces);
    setPlotLayout(layout);
  };

  const plotScatter = (x: number[], xLabel: string, yArrays: Record<string, number[]>) => {
    const traces: Plotly.Data[] = Object.entries(yArrays).map(([name, arr], i) => ({
      x,
      y: arr,
      type: "scattergl" as const,
      mode: "markers" as const,
      name,
      marker: { color: PLOT_COLORS[i % PLOT_COLORS.length], size: 4, opacity: 0.7 },
    }));
    setPlotData(traces);
    setPlotLayout({ xaxis: { title: { text: xLabel } } });
  };

  const plotHistogram = (yArrays: Record<string, number[]>) => {
    const traces: Plotly.Data[] = Object.entries(yArrays).map(([name, arr], i) => ({
      x: arr.filter((v) => !isNaN(v)),
      type: "histogram" as const,
      name,
      nbinsx: 50,
      opacity: 0.6,
      marker: { color: PLOT_COLORS[i % PLOT_COLORS.length] },
    }));
    setPlotData(traces);
    setPlotLayout({ barmode: "overlay" as const });
  };

  const plotCorrelationMatrix = (yArrays: Record<string, number[]>) => {
    const names = Object.keys(yArrays);
    const n = names.length;
    if (n < 2) {
      setStatus("Need at least 2 signals for correlation matrix");
      return;
    }

    // Compute correlation matrix
    const matrix: number[][] = [];
    const annotations: Partial<Plotly.Annotations>[] = [];
    for (let i = 0; i < n; i++) {
      const row: number[] = [];
      for (let j = 0; j < n; j++) {
        const r = pearsonR(yArrays[names[i]], yArrays[names[j]]);
        row.push(r);
        annotations.push({
          x: j,
          y: i,
          text: r.toFixed(2),
          showarrow: false,
          font: { color: Math.abs(r) < 0.7 ? "#1a1a1a" : "#f0f0f0", size: 10 },
        });
      }
      matrix.push(row);
    }

    setPlotData([
      {
        z: matrix,
        x: names,
        y: names,
        type: "heatmap" as const,
        colorscale: "RdYlGn" as any,
        zmin: -1,
        zmax: 1,
      },
    ]);
    setPlotLayout({ annotations });
  };

  const plotCrossCorrelation = (a: number[], b: number[], nameA: string, nameB: string) => {
    // Remove NaN pairs
    const validA: number[] = [], validB: number[] = [];
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
      if (!isNaN(a[i]) && !isNaN(b[i])) {
        validA.push(a[i]);
        validB.push(b[i]);
      }
    }
    if (validA.length < 2) {
      setStatus("Not enough valid data for cross-correlation");
      return;
    }

    // Normalize
    const meanA = validA.reduce((s, v) => s + v, 0) / validA.length;
    const meanB = validB.reduce((s, v) => s + v, 0) / validB.length;
    const stdA = Math.sqrt(validA.reduce((s, v) => s + (v - meanA) ** 2, 0) / validA.length) + 1e-12;
    const stdB = Math.sqrt(validB.reduce((s, v) => s + (v - meanB) ** 2, 0) / validB.length) + 1e-12;
    const normA = validA.map((v) => (v - meanA) / stdA);
    const normB = validB.map((v) => (v - meanB) / stdB);

    const corr = crossCorrelate(normA, normB).map((v) => v / validA.length);
    const lags = Array.from({ length: corr.length }, (_, i) => i - validB.length + 1);

    // Find peak
    let peakIdx = 0;
    let peakAbs = 0;
    for (let i = 0; i < corr.length; i++) {
      if (Math.abs(corr[i]) > peakAbs) {
        peakAbs = Math.abs(corr[i]);
        peakIdx = i;
      }
    }

    setPlotData([
      {
        x: lags,
        y: corr,
        type: "scatter" as const,
        mode: "lines" as const,
        line: { color: PLOT_COLORS[0], width: 1 },
        name: "Cross-Correlation",
      },
    ]);
    setPlotLayout({
      title: { text: `Cross-Correlation: ${nameA} vs ${nameB}` },
      xaxis: { title: { text: "Lag (samples)" } },
      yaxis: { title: { text: "Correlation" } },
      shapes: [
        {
          type: "line",
          x0: lags[peakIdx],
          x1: lags[peakIdx],
          y0: Math.min(...corr),
          y1: Math.max(...corr),
          line: { color: PLOT_COLORS[3], dash: "dash", width: 1 },
        },
      ],
      annotations: [
        {
          x: lags[peakIdx],
          y: corr[peakIdx],
          text: `peak lag=${lags[peakIdx]}<br>r=${corr[peakIdx].toFixed(3)}`,
          showarrow: true,
          arrowcolor: "#888888",
          font: { color: "#d4d4d4", size: 10 },
        },
      ],
    });
  };

  const plotCorrelationFinder = async () => {
    const tableNames = state.tables.map((t) => t.name);
    const allCols = state.numericColumns;

    // Build table columns (non-ts numeric)
    const tableColumns: Record<string, string[]> = {};
    for (const [tbl, cols] of Object.entries(allCols)) {
      const nonTs = cols.filter((c) => c !== "ts");
      if (nonTs.length > 0) tableColumns[tbl] = nonTs;
    }

    if (Object.keys(tableColumns).length < 2) {
      setStatus("Need at least 2 tables with numeric columns");
      return;
    }

    // Try ts-join first
    const tsJoinable: Record<string, string[]> = {};
    for (const [tbl, cols] of Object.entries(tableColumns)) {
      if (state.tablesWithTs.has(tbl)) tsJoinable[tbl] = cols;
    }

    let colNames: string[] = [];
    let rows: unknown[][] = [];

    if (Object.keys(tsJoinable).length >= 2) {
      try {
        const result = await rpcRequest("fetchJoinedColumns", { tableColumns: tsJoinable, on: "ts" });
        colNames = result.columns;
        rows = result.rows;
      } catch {}
    }

    if (rows.length === 0) {
      // Row-aligned fetch
      const allColNames: string[] = [];
      const allColumns: number[][] = [];
      let minRows = Infinity;

      for (const [tbl, cols] of Object.entries(tableColumns)) {
        const result = await rpcRequest("fetchColumns", { table: tbl, columns: cols });
        if (result.rows.length === 0) continue;
        minRows = Math.min(minRows, result.rows.length);
        for (let i = 0; i < result.columns.length; i++) {
          allColNames.push(`${tbl}.${result.columns[i]}`);
          allColumns.push(result.rows.map((r) => toFloat(r[i])));
        }
      }

      if (allColumns.length > 0 && minRows < Infinity) {
        colNames = allColNames;
        rows = Array.from({ length: minRows }, (_, r) =>
          allColumns.map((col) => col[r])
        );
      }
    }

    if (rows.length === 0 || colNames.length < 2) {
      setStatus("No data returned");
      return;
    }

    // Build numeric arrays
    const signalCols = colNames.filter((c) => c !== "ts");
    const colIdx: Record<string, number> = {};
    colNames.forEach((c, i) => (colIdx[c] = i));

    const arrays: Record<string, number[]> = {};
    for (const c of signalCols) {
      arrays[c] = rows.map((r) => toFloat(r[colIdx[c]]));
    }

    // Compute pairwise correlations
    const pairs: { a: string; b: string; r: number; rho: number }[] = [];
    const keys = Object.keys(arrays);
    for (let i = 0; i < keys.length; i++) {
      for (let j = i + 1; j < keys.length; j++) {
        // Filter valid pairs
        const validA: number[] = [], validB: number[] = [];
        for (let k = 0; k < arrays[keys[i]].length; k++) {
          if (!isNaN(arrays[keys[i]][k]) && !isNaN(arrays[keys[j]][k])) {
            validA.push(arrays[keys[i]][k]);
            validB.push(arrays[keys[j]][k]);
          }
        }
        if (validA.length < 3) continue;
        pairs.push({
          a: keys[i],
          b: keys[j],
          r: pearsonR(validA, validB),
          rho: spearmanR(validA, validB),
        });
      }
    }

    if (pairs.length === 0) {
      setStatus("No valid correlation pairs found");
      return;
    }

    // Sort by |r|, take top 20
    pairs.sort((a, b) => Math.abs(b.r) - Math.abs(a.r));
    const top = pairs.slice(0, 20);

    const labels = top.map((p) => `${p.a} vs ${p.b}`);
    const values = top.map((p) => p.r);
    const colors = values.map((v) => (v >= 0 ? "#27ae60" : "#d63031"));
    const annotations = top.map((p, i) => ({
      x: p.r + (p.r >= 0 ? 0.02 : -0.02),
      y: i,
      text: `r=${p.r.toFixed(2)} ρ=${p.rho.toFixed(2)}`,
      showarrow: false,
      xanchor: (p.r >= 0 ? "left" : "right") as "left" | "right",
      font: { color: "#d4d4d4", size: 8 },
    }));

    setPlotData([
      {
        y: labels,
        x: values,
        type: "bar" as const,
        orientation: "h" as const,
        marker: { color: colors },
      },
    ]);
    setPlotLayout({
      title: { text: "Top Correlations Across Tables" },
      xaxis: { title: { text: "Pearson r" } },
      yaxis: { autorange: "reversed" as const },
      annotations,
      margin: { l: 200 },
    });
    setStatus(`Found ${pairs.length} correlation pairs (${rows.length} rows)`);
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-52 flex-shrink-0 border-r border-telemu-border p-2 flex flex-col gap-2 overflow-auto">
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
          <span className="text-xs text-telemu-text-dim">Type:</span>
          <select
            value={plotType}
            onChange={(e) => setPlotType(e.target.value as PlotType)}
            className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text"
          >
            {PLOT_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-1.5 text-xs text-telemu-text cursor-pointer">
          <input
            type="checkbox"
            checked={normalizeChecked}
            onChange={(e) => setNormalize(e.target.checked)}
            className="accent-telemu-accent"
          />
          Normalize (0-1)
        </label>

        <FilterGroup filters={filters} onChange={setFilters} />

        <button
          onClick={handlePlot}
          className="w-full px-3 py-1.5 bg-telemu-accent text-telemu-text-bright rounded text-sm font-medium hover:bg-telemu-accent-hover active:bg-telemu-accent-pressed"
        >
          Plot
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
            Select signals and click Plot
          </div>
        )}
      </div>
    </div>
  );
}

import type Plotly from "plotly.js";
