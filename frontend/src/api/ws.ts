/** WebSocket client with auto-reconnect. */

import type { ServerMessage } from "./types";

type MessageHandler = (msg: ServerMessage) => void;

const WS_URL = `ws://${window.location.host}/ws`;
const RECONNECT_DELAY_MS = 2000;

class TeleMUWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private shouldReconnect = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.shouldReconnect = true;
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      // Subscribe to all channels
      this.send({
        type: "subscribe",
        channels: ["telemetry", "scoring", "status", "engineer"],
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as ServerMessage;
        for (const handler of this.handlers) {
          handler(msg);
        }
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  send(data: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsClient = new TeleMUWebSocket();
