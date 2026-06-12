from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from backend.app.alerts.events import AlertEvent, AlertEventType, event_bus
from backend.app.models import AlertSeverity
from backend.app.notifications.service import NotificationService

logger = logging.getLogger(__name__)

# Severity levels that should trigger immediate notifications
_NOTIFY_SEVERITIES: set[AlertSeverity] = {AlertSeverity.high, AlertSeverity.critical}

# Event types that should trigger notifications
_NOTIFY_EVENT_TYPES: set[AlertEventType] = {
    AlertEventType.created,
    AlertEventType.escalated,
}


def _make_callback(service: NotificationService) -> Callable[[AlertEvent], None]:
    """Return a sync callback suitable for the AlertEventBus.

    The event bus only supports synchronous callbacks, so we schedule the
    async notification work on the running event loop (if any).
    """

    def _on_alert_event(event: AlertEvent) -> None:
        # Filter: only notify on matching event types and severities
        if event.event_type not in _NOTIFY_EVENT_TYPES:
            return
        if event.severity not in _NOTIFY_SEVERITIES:
            logger.debug(
                "Skipping notification for alert %s — severity %s below threshold",
                event.alert_id,
                event.severity,
            )
            return

        logger.info(
            "NotificationRouter: dispatching notification for alert %s "
            "(type=%s, severity=%s)",
            event.alert_id,
            event.event_type.value,
            event.severity.value,
        )

        # Schedule the async notification — fire-and-forget
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(service.notify(event))
        except RuntimeError:
            # No running loop (e.g. called from sync code outside async)
            logger.warning(
                "No running event loop — running notification synchronously in new loop"
            )
            asyncio.run(service.notify(event))

    return _on_alert_event


# ---------------------------------------------------------------------------
# Module-level helpers for application lifecycle
# ---------------------------------------------------------------------------

_callback: Callable[[AlertEvent], None] | None = None


def start_notification_router(service: NotificationService) -> None:
    """Subscribe the notification router to the global :data:`event_bus`.

    Call once during application startup.
    """
    global _callback  # noqa: PLW0603
    if _callback is not None:
        logger.warning("Notification router already started — ignoring duplicate call")
        return

    _callback = _make_callback(service)
    event_bus.subscribe(_callback)
    logger.info("Notification router subscribed to AlertEventBus")


def stop_notification_router() -> None:
    """Unsubscribe the notification router from the global :data:`event_bus`.

    Call during application shutdown.
    """
    global _callback  # noqa: PLW0603
    if _callback is None:
        return
    event_bus.unsubscribe(_callback)
    _callback = None
    logger.info("Notification router unsubscribed from AlertEventBus")
