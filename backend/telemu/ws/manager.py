"""WebSocket connection manager — tracks clients and subscriptions."""

from __future__ import annotations

import json
import logging
import time

from fastapi import WebSocket

from telemu.ws import protocol

logger = logging.getLogger(__name__)


class ClientState:
    """Per-client state."""

    __slots__ = ("ws", "channels", "max_fps", "_last_send")

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self.channels: set[str] = set(protocol.DEFAULT_CHANNELS)
        self.max_fps: int = 60
        self._last_send: dict[str, float] = {}

    def should_send(self, channel: str) -> bool:
        """Rate-limit check per channel."""
        if channel not in self.channels:
            return False
        now = time.monotonic()
        min_interval = 1.0 / self.max_fps
        last = self._last_send.get(channel, 0)
        if now - last < min_interval:
            return False
        self._last_send[channel] = now
        return True


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self) -> None:
        self._clients: dict[int, ClientState] = {}

    @property
    def active_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients[id(ws)] = ClientState(ws)
        logger.info("WS client connected (%d total)", self.active_count)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.pop(id(ws), None)
        logger.info("WS client disconnected (%d remaining)", self.active_count)

    def get_client(self, ws: WebSocket) -> ClientState | None:
        return self._clients.get(id(ws))

    async def broadcast(self, channel: str, data: dict) -> None:
        """Send a message to all clients subscribed to the channel."""
        if not self._clients:
            return
        message = json.dumps(data)
        dead: list[int] = []
        for cid, client in self._clients.items():
            if client.should_send(channel):
                try:
                    await client.ws.send_text(message)
                except Exception:
                    dead.append(cid)
        for cid in dead:
            self._clients.pop(cid, None)

    async def send_to(self, ws: WebSocket, data: dict) -> None:
        """Send a message to a specific client."""
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            self.disconnect(ws)
