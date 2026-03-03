/** Hook for session management. */

import { useEffect } from "react";
import { useSessionStore } from "../stores/sessionStore";

export function useSession() {
  const { sessions, fetchSessions, openSession, activeSession, tables, loading, error } =
    useSessionStore();

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return { sessions, openSession, activeSession, tables, loading, error };
}
