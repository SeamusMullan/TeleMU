/** Live telemetry state from WebSocket. */

import { create } from "zustand";
import type { StatusMessage, LapInfoMessage } from "../api/types";

const HISTORY_SIZE = 200;

interface ChannelState {
  value: number;
  history: number[];
}

interface TelemetryState {
  connected: boolean;
  channels: Record<string, ChannelState>;
  status: StatusMessage;
  lapInfo: LapInfoMessage | null;

  setConnected: (v: boolean) => void;
  pushChannels: (data: Record<string, number>) => void;
  setStatus: (s: StatusMessage) => void;
  setLapInfo: (l: LapInfoMessage) => void;
}

const DEFAULT_STATUS: StatusMessage = {
  type: "status",
  drs: false,
  pit: false,
  flag: 0,
  tc: false,
  abs: false,
};

export const useTelemetryStore = create<TelemetryState>((set) => ({
  connected: false,
  channels: {},
  status: DEFAULT_STATUS,
  lapInfo: null,

  setConnected: (v) => set({ connected: v }),

  pushChannels: (data) =>
    set((state) => {
      const channels = { ...state.channels };
      for (const [key, value] of Object.entries(data)) {
        const existing = channels[key];
        const history = existing
          ? [...existing.history.slice(-(HISTORY_SIZE - 1)), value]
          : [value];
        channels[key] = { value, history };
      }
      return { channels };
    }),

  setStatus: (s) => set({ status: s }),
  setLapInfo: (l) => set({ lapInfo: l }),
}));
