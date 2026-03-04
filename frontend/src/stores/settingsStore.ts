/** Settings store — connection overrides and preferences. */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SettingsState {
  backendUrl: string;
  wsUrl: string;
  historySize: number;
  reconnectDelay: number;
  defaultEditMode: boolean;

  setBackendUrl: (url: string) => void;
  setWsUrl: (url: string) => void;
  setHistorySize: (size: number) => void;
  setReconnectDelay: (ms: number) => void;
  setDefaultEditMode: (v: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      backendUrl: "",
      wsUrl: "",
      historySize: 200,
      reconnectDelay: 2000,
      defaultEditMode: false,

      setBackendUrl: (backendUrl) => set({ backendUrl }),
      setWsUrl: (wsUrl) => set({ wsUrl }),
      setHistorySize: (historySize) => set({ historySize }),
      setReconnectDelay: (reconnectDelay) => set({ reconnectDelay }),
      setDefaultEditMode: (defaultEditMode) => set({ defaultEditMode }),
    }),
    { name: "telemu-settings" },
  ),
);
