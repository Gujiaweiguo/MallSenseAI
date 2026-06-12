from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.alerts.events import AlertEvent
from backend.app.models import (
    AlertSeverity,
    NotificationChannel,
    NotificationChannelType,
    NotificationGroup,
)
from backend.app.notifications.sms import SMSNotifier, StubSMSNotifier, TwilioSMSNotifier
from backend.app.notifications.wecom import WeComNotifier

logger = logging.getLogger(__name__)

# Severity levels that should trigger notifications
_HIGH_SEVERITIES: set[AlertSeverity] = {AlertSeverity.high, AlertSeverity.critical}

# Maximum send attempts with exponential back-off
_MAX_RETRIES = 3
_BASE_DELAY_S = 1.0


class NotificationService:
    """Orchestrates alert notifications across multiple channels.

    Loads notification groups from the database, matches them to the alert
    severity, and dispatches messages to the appropriate channels (WeCom,
    SMS, etc.).

    Notification failures are **always** caught and logged — they must never
    break the alert workflow.
    """

    def __init__(self, db_session_factory: sessionmaker[Session]) -> None:
        self._session_factory = db_session_factory
        # Cache of active channel notifiers keyed by (channel_type, channel_id)
        self._notifiers: dict[tuple[str, int], Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def notify(self, alert_event: AlertEvent) -> None:
        """Main entry point — dispatch notifications for *alert_event*.

        Silently catches all exceptions so that a notification failure never
        propagates to the caller.
        """
        try:
            groups = self._load_groups_for_severity(alert_event.severity)
            message = self._build_message(alert_event)
            for group in groups:
                await self._dispatch_group(group, message)
        except Exception:
            logger.exception(
                "Notification dispatch failed for alert %s (severity=%s)",
                alert_event.alert_id,
                alert_event.severity,
            )

    async def send_to_channel(
        self,
        channel_type: NotificationChannelType,
        channel_config: dict[str, Any],
        message: str,
    ) -> bool:
        """Send *message* through a single channel identified by *channel_type*.

        Returns True on success, False on failure.
        """
        try:
            notifier = self._get_notifier(channel_type, channel_config)
            return await self._retry_send(notifier, channel_type, channel_config, message)
        except Exception:
            logger.exception("send_to_channel failed for %s", channel_type)
            return False

    # ------------------------------------------------------------------
    # Severity → Group mapping
    # ------------------------------------------------------------------

    def _load_groups_for_severity(self, severity: AlertSeverity) -> list[NotificationGroup]:
        """Return enabled :class:`NotificationGroup` rows matching *severity*."""
        with self._session_factory() as session:
            stmt = (
                select(NotificationGroup)
                .where(NotificationGroup.enabled.is_(True))
            )
            groups = list(session.scalars(stmt).all())
            # Filter: a group applies when its ``channels`` JSON contains
            # a ``severities`` list that includes the current severity.
            matched: list[NotificationGroup] = []
            for group in groups:
                severities: list[str] = group.channels.get("severities", [])
                if not severities or severity.value in severities:
                    matched.append(group)
            # Eagerly load channels while the session is open
            for group in matched:
                _ = group.notification_channels  # noqa: F841
            return matched

    # ------------------------------------------------------------------
    # Dispatch helpers
    # ------------------------------------------------------------------

    async def _dispatch_group(self, group: NotificationGroup, message: str) -> None:
        """Send *message* to every enabled channel in *group*."""
        for channel in group.notification_channels:
            if not channel.enabled:
                logger.debug("Channel %s (id=%s) is disabled — skipping", channel.channel_type, channel.id)
                continue
            success = await self.send_to_channel(
                channel.channel_type,
                channel.config,
                message,
            )
            if not success:
                logger.warning(
                    "Notification to channel %s (id=%s) failed for group '%s'",
                    channel.channel_type,
                    channel.id,
                    group.name,
                )

    # ------------------------------------------------------------------
    # Notifier factory
    # ------------------------------------------------------------------

    def _get_notifier(self, channel_type: NotificationChannelType, config: dict[str, Any]) -> Any:
        """Return the appropriate notifier instance for *channel_type*."""
        if channel_type == NotificationChannelType.wecom:
            return WeComNotifier(webhook_url=config.get("webhook_url", ""))
        if channel_type == NotificationChannelType.sms:
            provider = config.get("provider", "stub")
            if provider == "twilio":
                return TwilioSMSNotifier(config)
            return StubSMSNotifier(config)
        logger.warning("Unsupported channel type: %s — using stub", channel_type)
        return StubSMSNotifier(config)

    # ------------------------------------------------------------------
    # Retry logic
    # ------------------------------------------------------------------

    async def _retry_send(
        self,
        notifier: Any,
        channel_type: NotificationChannelType,
        channel_config: dict[str, Any],
        message: str,
    ) -> bool:
        """Attempt to send with exponential back-off (1 s, 2 s, 4 s)."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                if isinstance(notifier, WeComNotifier):
                    # Use markdown for richer formatting
                    return await notifier.send_markdown(message)
                elif isinstance(notifier, SMSNotifier):
                    phone_numbers: list[str] = channel_config.get("phone_numbers", [])
                    return await notifier.send(phone_numbers, message)
                else:
                    logger.warning("Unknown notifier type: %s", type(notifier).__name__)
                    return False
            except Exception:
                logger.warning(
                    "Send attempt %d/%d failed for %s",
                    attempt,
                    _MAX_RETRIES,
                    channel_type,
                    exc_info=True,
                )
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY_S * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
        return False

    # ------------------------------------------------------------------
    # Message formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _build_message(alert_event: AlertEvent) -> str:
        """Format an :class:`AlertEvent` into a WeCom-markdown message."""
        md = (
            f"### 🚨 告警通知\n"
            f"> **告警ID**: {alert_event.alert_id}\n"
            f"> **摄像头ID**: {alert_event.camera_id}\n"
            f"> **严重级别**: {alert_event.severity.value}\n"
            f"> **事件类型**: {alert_event.event_type.value}\n"
            f"> **时间**: {alert_event.timestamp.isoformat()}\n"
        )
        if alert_event.metadata:
            roi_name = alert_event.metadata.get("roi_name")
            if roi_name:
                md += f"> **区域**: {roi_name}\n"
            details = alert_event.metadata.get("details")
            if details:
                md += f"> **详情**: {details}\n"
        return md
