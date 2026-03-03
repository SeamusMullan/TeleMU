/** Hook to connect WebSocket and pipe messages into Zustand stores. */

import { useEffect } from "react";
import { wsClient } from "../api/ws";
import { useTelemetryStore } from "../stores/telemetryStore";
import type { ServerMessage } from "../api/types";

export function useTelemetry() {
  const { pushChannels, setStatus, setLapInfo, setConnected } =
    useTelemetryStore();

  useEffect(() => {
    const handler = (msg: ServerMessage) => {
      switch (msg.type) {
        case "telemetry":
          pushChannels(msg.channels);
          break;
        case "status":
          setStatus(msg);
          break;
        case "lap_info":
          setLapInfo(msg);
          break;
      }
    };

    const unsub = wsClient.subscribe(handler);
    wsClient.connect();
    setConnected(true);

    return () => {
      unsub();
      wsClient.disconnect();
      setConnected(false);
    };
  }, [pushChannels, setStatus, setLapInfo, setConnected]);
}
