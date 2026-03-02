import React, { useState, useCallback } from "react";
import { useApp } from "../store/AppContext";
import { rpcRequest } from "../hooks/useRPC";
import { SignalTree, type SelectedSignals } from "./SignalTree";
import { FilterGroup } from "./FilterGroup";
import { PlotContainer } from "./PlotContainer";
import { PLOT_COLORS } from "../lib/theme";
import { DEFAULT_FILTERS, toFloat, type FilterState } from "../lib/filters";

const _LAT_TABLE_NAMES = new Set([
  "latitude", "lat", "gps_lat", "gps latitude", "gpslat", "gps_latitude",
]);
const _LON_TABLE_NAMES = new Set([
  "longitude", "lon", "lng", "gps_lon", "gps longitude", "gpslon", "gpslng", "gps_longitude",
]);
const _SPEED_TABLE_NAMES = new Set([
  "speed", "gps speed", "gps_speed", "gpsspeed", "velocity",
]);

export function TrackViewer() {
  const { state } = useApp();
  const [colorSignals, setColorSignals] = useState<SelectedSignals>({});
  const [filters, setFilters] = useState<FilterState>({ ...DEFAULT_FILTERS, excludeZeros: false, excludeNaN: false });
  const [plotData, setPlotData] = useState<Plotly.Data[]>([]);
  const [plotLayout, setPlotLayout] = useState<Partial<Plotly.Layout>>({});
  const [status, setStatus] = useState("");

  const findGpsTables = useCallback((): {
    latTable: string | null;
    lonTable: string | null;
  } => {
    let latTable: string | null = null;
    let lonTable: string | null = null;
    for (const t of state.tables) {
      const lower = t.name.toLowerCase().trim();
      if (_LAT_TABLE_NAMES.has(lower) && !latTable) latTable = t.name;
      else if (_LON_TABLE_NAMES.has(lower) && !lonTable) lonTable = t.name;
    }
    return { latTable, lonTable };
  }, [state.tables]);

  const fetchValue = useCallback(async (table: string): Promise<number[] | null> => {
    const schema = await rpcRequest("tableSchema", { table });
    const colNames = schema.map((c) => c.name);
    let valCol: string | null = null;
    if (colNames.includes("value")) {
      valCol = "value";
    } else {
      const numCols = state.numericColumns[table] ?? [];
      const nonTs = numCols.filter((c) => c !== "ts");
      if (nonTs.length > 0) valCol = nonTs[0];
    }
    if (!valCol) return null;
    const result = await rpcRequest("fetchColumns", { table, columns: [valCol] });
    return result.rows.map((r) => toFloat(r[0]));
  }, [state.numericColumns]);

  const handlePlot = useCallback(async () => {
    const { latTable, lonTable } = findGpsTables();
    if (!latTable || !lonTable) {
      const missing = [];
      if (!latTable) missing.push("latitude");
      if (!lonTable) missing.push("longitude");
      setStatus(`No table found for: ${missing.join(", ")}`);
      setPlotData([]);
      return;
    }

    const lat = await fetchValue(latTable);
    const lon = await fetchValue(lonTable);
    if (!lat || !lon) {
      setStatus("Could not read value column from GPS tables");
      return;
    }

    const n = Math.min(lat.length, lon.length);
    const validLat: number[] = [];
    const validLon: number[] = [];
    const validIndices: number[] = [];

    for (let i = 0; i < n; i++) {
      if (!isNaN(lat[i]) && !isNaN(lon[i]) && !(lat[i] === 0 && lon[i] === 0)) {
        validLat.push(lat[i]);
        validLon.push(lon[i]);
        validIndices.push(i);
      }
    }

    if (validLat.length < 2) {
      setStatus("Not enough valid GPS points");
      return;
    }

    // Apply value filters
    let filteredLat = validLat;
    let filteredLon = validLon;
    let excluded = 0;

    if (filters.valMin !== null || filters.valMax !== null || filters.excludeNaN || filters.excludeZeros) {
      const keepLat: number[] = [];
      const keepLon: number[] = [];
      for (let i = 0; i < validLat.length; i++) {
        let keep = true;
        if (filters.valMin !== null && (validLat[i] < filters.valMin || validLon[i] < filters.valMin)) keep = false;
        if (filters.valMax !== null && (validLat[i] > filters.valMax || validLon[i] > filters.valMax)) keep = false;
        if (keep) {
          keepLat.push(validLat[i]);
          keepLon.push(validLon[i]);
        } else {
          excluded++;
        }
      }
      filteredLat = keepLat;
      filteredLon = keepLon;
    }

    if (filteredLat.length < 2) {
      setStatus("Not enough points after filtering");
      return;
    }

    // Get colour-by signal
    let colorData: number[] | null = null;
    let colorLabel: string | null = null;
    for (const [tbl, cols] of Object.entries(colorSignals)) {
      if (tbl === latTable || tbl === lonTable) continue;
      if (cols.length > 0) {
        const raw = await fetchValue(tbl);
        if (raw) {
          // Align to GPS length
          const aligned = raw.slice(0, n);
          const validAligned = validIndices.map((i) => i < aligned.length ? aligned[i] : NaN);
          if (validAligned.some((v) => !isNaN(v))) {
            colorData = validAligned.slice(0, filteredLat.length);
            colorLabel = tbl;
          }
        }
        break;
      }
    }

    // Build plot traces
    const traces: Plotly.Data[] = [];

    // Base track line
    traces.push({
      x: filteredLon,
      y: filteredLat,
      type: "scatter",
      mode: "lines",
      line: { color: PLOT_COLORS[0], width: 1.5 },
      name: "Track",
      hoverinfo: "skip",
    });

    // Colour overlay
    if (colorData && colorData.some((v) => !isNaN(v))) {
      traces.push({
        x: filteredLon.slice(0, colorData.length),
        y: filteredLat.slice(0, colorData.length),
        type: "scattergl",
        mode: "markers",
        marker: {
          color: colorData,
          colorscale: "Plasma",
          showscale: true,
          size: 4,
          colorbar: {
            title: { text: colorLabel ?? "", font: { color: "#d4d4d4" } },
            tickfont: { color: "#d4d4d4" },
          },
        },
        name: colorLabel ?? "Color",
        hovertemplate: `${colorLabel}: %{marker.color:.2f}<extra></extra>`,
      });
    }

    // Start/Finish markers
    traces.push({
      x: [filteredLon[0]],
      y: [filteredLat[0]],
      type: "scatter",
      mode: "markers",
      marker: { color: "#27ae60", size: 12, symbol: "circle" },
      name: "Start",
    });
    traces.push({
      x: [filteredLon[filteredLon.length - 1]],
      y: [filteredLat[filteredLat.length - 1]],
      type: "scatter",
      mode: "markers",
      marker: { color: "#d63031", size: 12, symbol: "square" },
      name: "Finish",
    });

    setPlotData(traces);
    setPlotLayout({
      title: { text: colorLabel ? `Track Map — colour: ${colorLabel}` : "Track Map" },
      xaxis: { title: { text: "Longitude" }, scaleanchor: "y" },
      yaxis: { title: { text: "Latitude" } },
    });

    let statusMsg = `Track map: ${filteredLat.length} points, ${excluded} excluded`;
    if (colorLabel && colorData) {
      const colorN = colorData.filter((v) => !isNaN(v)).length;
      if (colorN < filteredLat.length) {
        statusMsg += ` (colour: ${colorLabel}, ${colorN}/${filteredLat.length} points)`;
      } else {
        statusMsg += ` (colour: ${colorLabel})`;
      }
    }
    setStatus(statusMsg);
  }, [findGpsTables, fetchValue, colorSignals, filters, state]);

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-52 flex-shrink-0 border-r border-telemu-border p-2 flex flex-col gap-2 overflow-auto">
        <div className="text-xs font-medium text-telemu-text-dim">Colour-by Signal</div>
        <SignalTree onSelectionChange={setColorSignals} singleSelect />

        <FilterGroup filters={filters} onChange={setFilters} showRange={false} />

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
            Click Plot to view GPS track
          </div>
        )}
      </div>
    </div>
  );
}

import type Plotly from "plotly.js";
