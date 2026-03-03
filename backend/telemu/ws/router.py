"""WebSocket endpoint."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from telemu.ws import protocol
from telemu.ws.manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            client = manager.get_client(ws)
            if client is None:
                break

            if msg_type == protocol.SUBSCRIBE:
                channels = msg.get("channels", [])
                valid = {c for c in channels if c in protocol.CHANNELS}
                client.channels = valid
                logger.debug("Client subscribed to: %s", valid)

            elif msg_type == protocol.THROTTLE:
                fps = msg.get("max_fps", 60)
                client.max_fps = max(1, min(120, fps))

            # record/playback handled by other subsystems via app state

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        manager.disconnect(ws)
