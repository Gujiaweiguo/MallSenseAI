"""WebSocket endpoint for real-time alert event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.app.alerts.events import AlertEvent, AlertEventBus, event_bus
from backend.app.auth.jwt import JWTError, decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


class AlertWebSocketManager:
    """Manages WebSocket connections and broadcasts AlertEvents."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._callback = self._on_event

    def start(self, bus: AlertEventBus) -> None:
        bus.subscribe(self._callback)
        logger.info("AlertWebSocketManager subscribed to event_bus")

    def stop(self, bus: AlertEventBus) -> None:
        bus.unsubscribe(self._callback)
        logger.info("AlertWebSocketManager unsubscribed from event_bus")

    async def accept(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WS client connected — total=%d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("WS client disconnected — total=%d", len(self._connections))

    def _on_event(self, event: AlertEvent) -> None:
        data = _serialize_event(event)
        payload = json.dumps(data, default=_json_default)
        for ws in list(self._connections):
            asyncio.get_event_loop().create_task(self._safe_send(ws, payload))

    @staticmethod
    async def _safe_send(ws: WebSocket, payload: str) -> None:
        try:
            await ws.send_text(payload)
        except Exception:
            logger.debug("Failed to send WS message — client likely disconnected")


ws_manager = AlertWebSocketManager()


def _serialize_event(event: AlertEvent) -> dict:
    return {
        "event_type": event.event_type.value,
        "alert_id": event.alert_id,
        "camera_id": event.camera_id,
        "severity": event.severity.value,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "metadata": event.metadata,
    }


def _json_default(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@router.websocket("/ws/alerts")
async def alerts_ws(ws: WebSocket, token: str = Query(...)) -> None:
    try:
        decode_access_token(token)
    except JWTError:
        await ws.close(code=4001, reason="Invalid or expired token")
        return

    await ws_manager.accept(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(ws)
