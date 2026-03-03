/** Session/database state for post-session analysis. */

import { create } from "zustand";
import type { SessionInfo, TableInfo } from "../api/types";
import { api } from "../api/rest";

interface SessionState {
  sessions: SessionInfo[];
  activeSession: string | null;
  tables: TableInfo[];
  loading: boolean;
  error: string | null;

  fetchSessions: () => Promise<void>;
  openSession: (filename: string) => Promise<void>;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  activeSession: null,
  tables: [],
  loading: false,
  error: null,

  fetchSessions: async () => {
    set({ loading: true, error: null });
    try {
      const sessions = await api.sessions();
      set({ sessions, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  openSession: async (filename: string) => {
    set({ loading: true, error: null });
    try {
      await api.openSession(filename);
      const tables = await api.tables();
      set({ activeSession: filename, tables, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },
}));
