export const PLOT_COLORS = [
  "#e8751a", // accent orange
  "#f5a623", // amber
  "#00bcd4", // cyan
  "#e040fb", // magenta
  "#27ae60", // green
  "#d63031", // red
  "#4fc3f7", // sky blue
  "#ab47bc", // violet
] as const;

export const PLOTLY_DARK_LAYOUT: Partial<Plotly.Layout> = {
  paper_bgcolor: "#1a1a1a",
  plot_bgcolor: "#242424",
  font: { color: "#d4d4d4", family: "Inter, sans-serif" },
  xaxis: {
    gridcolor: "#3a3a3a",
    zerolinecolor: "#3a3a3a",
    color: "#d4d4d4",
  },
  yaxis: {
    gridcolor: "#3a3a3a",
    zerolinecolor: "#3a3a3a",
    color: "#d4d4d4",
  },
  legend: {
    bgcolor: "#242424",
    bordercolor: "#3a3a3a",
    borderwidth: 1,
    font: { color: "#d4d4d4" },
  },
  margin: { l: 60, r: 30, t: 40, b: 50 },
  autosize: true,
};

/** Merge a custom layout on top of the dark theme defaults. */
export function darkLayout(
  overrides: Partial<Plotly.Layout> = {}
): Partial<Plotly.Layout> {
  return {
    ...PLOTLY_DARK_LAYOUT,
    ...overrides,
    xaxis: { ...(PLOTLY_DARK_LAYOUT.xaxis as object), ...(overrides.xaxis as object) },
    yaxis: { ...(PLOTLY_DARK_LAYOUT.yaxis as object), ...(overrides.yaxis as object) },
  };
}

import type Plotly from "plotly.js";
