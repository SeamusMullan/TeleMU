import React from "react";
import Plot from "react-plotly.js";
import { darkLayout } from "../lib/theme";

interface PlotContainerProps {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  className?: string;
}

export function PlotContainer({ data, layout = {}, className = "" }: PlotContainerProps) {
  return (
    <div className={`w-full h-full ${className}`}>
      <Plot
        data={data}
        layout={darkLayout(layout)}
        config={{
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ["lasso2d", "select2d"],
        }}
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}

import type Plotly from "plotly.js";
