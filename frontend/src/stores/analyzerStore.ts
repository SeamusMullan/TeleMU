/** Analyzer state — selected channels, chart type, time range. */

import { create } from "zustand";

const CHART_COLORS = [
  "#e8751a", "#4fc3f7", "#27ae60", "#d63031", "#f5a623",
  "#00bcd4", "#9b59b6", "#e74c3c", "#2ecc71", "#3498db",
];

export type ChartType = "line" | "scatter" | "histogram";

interface ChannelSelection {
  channel: string;
  color: string;
}

interface AnalyzerState {
  selectedChannels: ChannelSelection[];
  chartType: ChartType;
  timeRange: { start: number | null; end: number | null };

  toggleChannel: (channel: string) => void;
  setChartType: (type: ChartType) => void;
  setTimeRange: (range: { start: number | null; end: number | null }) => void;
  clearChannels: () => void;
}

export const useAnalyzerStore = create<AnalyzerState>((set) => ({
  selectedChannels: [],
  chartType: "line",
  timeRange: { start: null, end: null },

  toggleChannel: (channel) =>
    set((state) => {
      const exists = state.selectedChannels.find((c) => c.channel === channel);
      if (exists) {
        return {
          selectedChannels: state.selectedChannels.filter((c) => c.channel !== channel),
        };
      }
      const usedColors = new Set(state.selectedChannels.map((c) => c.color));
      const color = CHART_COLORS.find((c) => !usedColors.has(c)) ?? CHART_COLORS[0]!;
      return {
        selectedChannels: [...state.selectedChannels, { channel, color }],
      };
    }),

  setChartType: (chartType) => set({ chartType }),

  setTimeRange: (timeRange) => set({ timeRange }),

  clearChannels: () => set({ selectedChannels: [] }),
}));
