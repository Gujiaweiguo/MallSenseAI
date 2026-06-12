from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.app.models import AlertSeverity


class AlertEventType(str, enum.Enum):
    created = "created"
    confirmed = "confirmed"
    resolved = "resolved"
    false_positive = "false_positive"
    escalated = "escalated"


@dataclass
class AlertEvent:
    event_type: AlertEventType
    alert_id: int
    camera_id: int
    severity: AlertSeverity
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


# Type alias for subscriber callbacks
AlertEventCallback = Callable[[AlertEvent], None]


class AlertEventBus:
    """Simple in-memory pub/sub event bus for alert lifecycle events.

    Will later be connected to notification channels (T08).
    """

    def __init__(self) -> None:
        self._subscribers: list[AlertEventCallback] = []
        self._events: list[AlertEvent] = []

    def publish(self, event: AlertEvent) -> None:
        """Store event and notify all subscribers."""
        self._events.append(event)
        for callback in self._subscribers:
            callback(event)

    def subscribe(self, callback: AlertEventCallback) -> None:
        """Register a callback to be invoked on every alert event."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: AlertEventCallback) -> None:
        """Remove a previously registered callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def get_recent_events(self, limit: int = 50) -> list[AlertEvent]:
        """Return the most recent events, newest first."""
        return list(reversed(self._events[-limit:]))


# Module-level singleton for application-wide use
event_bus = AlertEventBus()
