/** Default widget layouts for each page. */

import type { Layout } from "react-grid-layout";
import type { WidgetInstance, PageLayout, LayoutProfile } from "../stores/layoutStore";

// --- Dashboard defaults (translated from DashboardPage.tsx GAUGES/SPARKLINES) ---

const dashboardWidgets: WidgetInstance[] = [
  // Status row
  { id: "status_row_1", type: "status_row", config: {} },
  // Recording controls
  { id: "recording_1", type: "recording", config: {} },
  // Gauges
  { id: "gauge_speed", type: "gauge", config: { channel: "speed", label: "Speed", min: 0, max: 340, unit: "km/h", warnHigh: 320, decimals: 0 } },
  { id: "gauge_rpm", type: "gauge", config: { channel: "rpm", label: "RPM", min: 0, max: 9000, unit: "rpm", warnHigh: 8500, decimals: 0, dynamicMaxChannel: "rpm_max" } },
  { id: "gauge_throttle", type: "gauge", config: { channel: "throttle", label: "Throttle", min: 0, max: 100, unit: "%", decimals: 0 } },
  { id: "gauge_brake", type: "gauge", config: { channel: "brake", label: "Brake", min: 0, max: 100, unit: "%", warnHigh: 95, decimals: 0 } },
  { id: "gauge_gear", type: "gauge", config: { channel: "gear", label: "Gear", min: 0, max: 8, unit: "", decimals: 0 } },
  { id: "gauge_steering", type: "gauge", config: { channel: "steering", label: "Steering", min: -450, max: 450, unit: "°", decimals: 1 } },
  // Sparklines
  { id: "spark_tyre_fl", type: "sparkline", config: { channel: "tyre_fl", label: "Tyre FL", min: 50, max: 130, unit: "°C", warnHigh: 115 } },
  { id: "spark_tyre_fr", type: "sparkline", config: { channel: "tyre_fr", label: "Tyre FR", min: 50, max: 130, unit: "°C", warnHigh: 115 } },
  { id: "spark_tyre_rl", type: "sparkline", config: { channel: "tyre_rl", label: "Tyre RL", min: 50, max: 130, unit: "°C", warnHigh: 115 } },
  { id: "spark_tyre_rr", type: "sparkline", config: { channel: "tyre_rr", label: "Tyre RR", min: 50, max: 130, unit: "°C", warnHigh: 115 } },
  { id: "spark_fuel", type: "sparkline", config: { channel: "fuel", label: "Fuel", min: 0, max: 110, unit: "L", warnLow: 5, dynamicMaxChannel: "fuel_capacity" } },
  { id: "spark_brake_temp", type: "sparkline", config: { channel: "brake_temp", label: "Brake Temp", min: 100, max: 900, unit: "°C", warnHigh: 800 } },
  // Lap info
  { id: "lap_info_1", type: "lap_info", config: {} },
  // Streaming panel
  { id: "streaming_1", type: "streaming_panel", config: {} },
];

const dashboardLayouts: { lg: Layout[]; md: Layout[]; sm: Layout[] } = {
  lg: [
    // Status row — full width
    { i: "status_row_1", x: 0, y: 0, w: 8, h: 2, minW: 4, minH: 2 },
    // Recording — right of status
    { i: "recording_1", x: 8, y: 0, w: 4, h: 2, minW: 3, minH: 2 },
    // Gauges — 6 across, 2 cols each
    { i: "gauge_speed", x: 0, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_rpm", x: 2, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_throttle", x: 4, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_brake", x: 6, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_gear", x: 8, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_steering", x: 10, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    // Sparklines — 3 per row, 4 cols each
    { i: "spark_tyre_fl", x: 0, y: 6, w: 4, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_fr", x: 4, y: 6, w: 4, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_rl", x: 8, y: 6, w: 4, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_rr", x: 0, y: 8, w: 4, h: 2, minW: 3, minH: 2 },
    { i: "spark_fuel", x: 4, y: 8, w: 4, h: 2, minW: 3, minH: 2 },
    { i: "spark_brake_temp", x: 8, y: 8, w: 4, h: 2, minW: 3, minH: 2 },
    // Lap info + Streaming — right side
    { i: "lap_info_1", x: 0, y: 10, w: 3, h: 4, minW: 2, minH: 3 },
    { i: "streaming_1", x: 3, y: 10, w: 3, h: 4, minW: 2, minH: 3 },
  ],
  md: [
    { i: "status_row_1", x: 0, y: 0, w: 6, h: 2, minW: 4, minH: 2 },
    { i: "recording_1", x: 6, y: 0, w: 4, h: 2, minW: 3, minH: 2 },
    { i: "gauge_speed", x: 0, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_rpm", x: 2, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_throttle", x: 4, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_brake", x: 6, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_gear", x: 8, y: 2, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_steering", x: 0, y: 6, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "spark_tyre_fl", x: 0, y: 10, w: 5, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_fr", x: 5, y: 10, w: 5, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_rl", x: 0, y: 12, w: 5, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_rr", x: 5, y: 12, w: 5, h: 2, minW: 3, minH: 2 },
    { i: "spark_fuel", x: 0, y: 14, w: 5, h: 2, minW: 3, minH: 2 },
    { i: "spark_brake_temp", x: 5, y: 14, w: 5, h: 2, minW: 3, minH: 2 },
    { i: "lap_info_1", x: 0, y: 16, w: 5, h: 4, minW: 2, minH: 3 },
    { i: "streaming_1", x: 5, y: 16, w: 5, h: 4, minW: 2, minH: 3 },
  ],
  sm: [
    { i: "status_row_1", x: 0, y: 0, w: 6, h: 2, minW: 4, minH: 2 },
    { i: "recording_1", x: 0, y: 2, w: 6, h: 2, minW: 3, minH: 2 },
    { i: "gauge_speed", x: 0, y: 4, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_rpm", x: 2, y: 4, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_throttle", x: 4, y: 4, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_brake", x: 0, y: 8, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_gear", x: 2, y: 8, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "gauge_steering", x: 4, y: 8, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "spark_tyre_fl", x: 0, y: 12, w: 6, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_fr", x: 0, y: 14, w: 6, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_rl", x: 0, y: 16, w: 6, h: 2, minW: 3, minH: 2 },
    { i: "spark_tyre_rr", x: 0, y: 18, w: 6, h: 2, minW: 3, minH: 2 },
    { i: "spark_fuel", x: 0, y: 20, w: 6, h: 2, minW: 3, minH: 2 },
    { i: "spark_brake_temp", x: 0, y: 22, w: 6, h: 2, minW: 3, minH: 2 },
    { i: "lap_info_1", x: 0, y: 24, w: 6, h: 4, minW: 2, minH: 3 },
    { i: "streaming_1", x: 0, y: 28, w: 6, h: 4, minW: 2, minH: 3 },
  ],
};

// --- Explorer defaults ---

const explorerWidgets: WidgetInstance[] = [
  { id: "session_picker_1", type: "session_picker", config: {} },
  { id: "schema_browser_1", type: "schema_browser", config: {} },
  { id: "data_table_1", type: "data_table", config: {} },
  { id: "sql_query_1", type: "sql_query", config: {} },
];

const explorerLayouts: { lg: Layout[]; md: Layout[]; sm: Layout[] } = {
  lg: [
    { i: "session_picker_1", x: 0, y: 0, w: 3, h: 2, minW: 2, minH: 2 },
    { i: "schema_browser_1", x: 0, y: 2, w: 3, h: 10, minW: 2, minH: 4 },
    { i: "data_table_1", x: 3, y: 0, w: 9, h: 8, minW: 4, minH: 4 },
    { i: "sql_query_1", x: 3, y: 8, w: 9, h: 4, minW: 4, minH: 3 },
  ],
  md: [
    { i: "session_picker_1", x: 0, y: 0, w: 4, h: 2, minW: 2, minH: 2 },
    { i: "schema_browser_1", x: 0, y: 2, w: 4, h: 8, minW: 2, minH: 4 },
    { i: "data_table_1", x: 4, y: 0, w: 6, h: 7, minW: 4, minH: 4 },
    { i: "sql_query_1", x: 4, y: 7, w: 6, h: 3, minW: 4, minH: 3 },
  ],
  sm: [
    { i: "session_picker_1", x: 0, y: 0, w: 6, h: 2, minW: 2, minH: 2 },
    { i: "schema_browser_1", x: 0, y: 2, w: 6, h: 6, minW: 2, minH: 4 },
    { i: "data_table_1", x: 0, y: 8, w: 6, h: 6, minW: 4, minH: 4 },
    { i: "sql_query_1", x: 0, y: 14, w: 6, h: 4, minW: 4, minH: 3 },
  ],
};

// --- Analyzer defaults ---

const analyzerWidgets: WidgetInstance[] = [
  { id: "channel_selector_1", type: "channel_selector", config: {} },
  { id: "echart_1", type: "echart", config: {} },
];

const analyzerLayouts: { lg: Layout[]; md: Layout[]; sm: Layout[] } = {
  lg: [
    { i: "channel_selector_1", x: 0, y: 0, w: 3, h: 12, minW: 2, minH: 4 },
    { i: "echart_1", x: 3, y: 0, w: 9, h: 12, minW: 4, minH: 4 },
  ],
  md: [
    { i: "channel_selector_1", x: 0, y: 0, w: 3, h: 10, minW: 2, minH: 4 },
    { i: "echart_1", x: 3, y: 0, w: 7, h: 10, minW: 4, minH: 4 },
  ],
  sm: [
    { i: "channel_selector_1", x: 0, y: 0, w: 6, h: 6, minW: 2, minH: 4 },
    { i: "echart_1", x: 0, y: 6, w: 6, h: 8, minW: 4, minH: 4 },
  ],
};

// --- Page layout builders ---

function makePage(id: string, name: string, widgets: WidgetInstance[], layouts: typeof dashboardLayouts): PageLayout {
  return { id, name, gridLayouts: layouts, widgets, locked: false };
}

export const DEFAULT_PAGES: Record<string, PageLayout> = {
  dashboard: makePage("dashboard", "Dashboard", dashboardWidgets, dashboardLayouts),
  explorer: makePage("explorer", "Explorer", explorerWidgets, explorerLayouts),
  analyzer: makePage("analyzer", "Analyzer", analyzerWidgets, analyzerLayouts),
};

export function createDefaultProfile(): LayoutProfile {
  return {
    id: "default",
    name: "Default",
    pages: { ...DEFAULT_PAGES },
  };
}
