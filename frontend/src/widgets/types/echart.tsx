/** EChart widget type — wraps TimeSeriesChart. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import TimeSeriesChart from "../../components/analyzer/TimeSeriesChart";

const EChartWrapper = memo(function EChartWrapper({ width, height }: WidgetProps) {
  return <TimeSeriesChart width={width} height={height} />;
});

registerWidget({
  type: "echart",
  name: "Time Series Chart",
  description: "ECharts time-series plot with zoom and pan",
  icon: "📈",
  defaultW: 9,
  defaultH: 12,
  minW: 4,
  minH: 4,
  configFields: [],
  component: EChartWrapper,
});
