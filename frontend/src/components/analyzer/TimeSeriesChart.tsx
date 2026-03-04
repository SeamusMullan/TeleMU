/** Time series chart — ECharts with zoom, pan, crosshair, multi-signal overlay. */

import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTelemetryStore } from "../../stores/telemetryStore";
import { useAnalyzerStore } from "../../stores/analyzerStore";

interface TimeSeriesChartProps {
  width: number;
  height: number;
}

export default function TimeSeriesChart({ width, height }: TimeSeriesChartProps) {
  const channels = useTelemetryStore((s) => s.channels);
  const { selectedChannels, chartType } = useAnalyzerStore();

  const option = useMemo(() => {
    if (selectedChannels.length === 0) {
      return {
        title: {
          text: "Select channels to plot",
          left: "center",
          top: "middle",
          textStyle: { color: "#666", fontSize: 14 },
        },
        backgroundColor: "transparent",
      };
    }

    const series = selectedChannels.map((sel) => {
      const ch = channels[sel.channel];
      const data = ch?.history ?? [];
      return {
        name: sel.channel,
        type: chartType === "histogram" ? "bar" : chartType,
        data: data.map((v, i) => [i, v]),
        smooth: chartType === "line",
        showSymbol: chartType === "scatter",
        symbolSize: chartType === "scatter" ? 4 : 0,
        lineStyle: { color: sel.color, width: 1.5 },
        itemStyle: { color: sel.color },
        areaStyle: chartType === "line" ? { color: sel.color, opacity: 0.05 } : undefined,
      };
    });

    return {
      backgroundColor: "transparent",
      legend: {
        data: selectedChannels.map((s) => s.channel),
        top: 8,
        textStyle: { color: "#999", fontSize: 10 },
      },
      tooltip: {
        trigger: "axis" as const,
        backgroundColor: "#1a1a1a",
        borderColor: "#333",
        textStyle: { color: "#ccc", fontSize: 10 },
        axisPointer: { type: "cross" as const },
      },
      xAxis: {
        type: "value" as const,
        name: "Sample",
        nameTextStyle: { color: "#666" },
        axisLine: { lineStyle: { color: "#333" } },
        axisLabel: { color: "#666", fontSize: 10 },
        splitLine: { lineStyle: { color: "#222" } },
      },
      yAxis: {
        type: "value" as const,
        axisLine: { lineStyle: { color: "#333" } },
        axisLabel: { color: "#666", fontSize: 10 },
        splitLine: { lineStyle: { color: "#222" } },
      },
      dataZoom: [
        { type: "inside" as const, xAxisIndex: 0 },
        { type: "slider" as const, xAxisIndex: 0, height: 20, bottom: 8, borderColor: "#333", textStyle: { color: "#666" } },
      ],
      series,
      grid: { top: 40, right: 20, bottom: 40, left: 50 },
    };
  }, [selectedChannels, channels, chartType]);

  // Use container size if available, fall back to reasonable defaults
  const chartHeight = height > 100 ? height - 16 : 400;
  const chartWidth = width > 100 ? width - 16 : undefined;

  return (
    <div className="h-full w-full p-2">
      <ReactECharts
        option={option}
        style={{ height: chartHeight, width: chartWidth || "100%" }}
        notMerge
        lazyUpdate
        theme="dark"
      />
    </div>
  );
}
