"""Critical alert path for fire/smoke detections.

Bypasses normal rule evaluation and directly creates *critical* severity
alerts with immediate notification via the event bus.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.alerts.events import AlertEvent, AlertEventType, event_bus
from backend.app.alerts.service import AlertCandidate, AlertService
from backend.app.detectors.base import DetectionResult
from backend.app.models import Alert, AlertSeverity, RuleType

logger = logging.getLogger(__name__)


class CriticalAlertHandler:
    """Handles fire/smoke detections by creating critical alerts immediately.

    Key behaviours:
    * **Bypasses normal rule evaluation** — every detection becomes a
      ``critical`` alert.
    * **Skips cooldown** — critical events are always recorded.
    * **Publishes an ``escalated`` event** on the :class:`AlertEventBus`
      immediately after creation.
    * **Logs every detection** regardless of whether an alert was created.
    """

    @staticmethod
    def handle_fire_smoke_detection(
        camera_id: int,
        detections: list[DetectionResult],
        db: Session,
        *,
        evidence_image_path: str | None = None,
    ) -> Alert | None:
        """Process fire/smoke detections and create a critical alert.

        Parameters
        ----------
        camera_id:
            The camera that produced the detections.
        detections:
            Non-empty list of fire/smoke :class:`DetectionResult` objects.
        db:
            Active database session.
        evidence_image_path:
            Optional path to the annotated evidence image.

        Returns
        -------
        Alert or None
            The created alert, or *None* if no detections were provided.
        """
        # Always log detections, even if we don't end up creating an alert.
        for det in detections:
            area_ratio = det.metadata.get("area_ratio", 0.0)
            logger.warning(
                "FIRE/SMOKE detection — camera=%d label=%s confidence=%.3f "
                "polygon=%s area_ratio=%.4f",
                camera_id,
                det.label,
                det.confidence,
                det.polygon,
                area_ratio,
            )

        if not detections:
            return None

        # Build metadata from detections
        metadata: dict[str, Any] = {
            "detection_count": len(detections),
            "detections": [
                {
                    "label": d.label,
                    "confidence": d.confidence,
                    "polygon": list(d.polygon),
                    "area_ratio": d.metadata.get("area_ratio", 0.0),
                }
                for d in detections
            ],
            "detected_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        # Build alert candidate — always critical, bypasses rules.
        candidate = AlertCandidate(
            camera_id=camera_id,
            alert_type=RuleType.fire_smoke,
            severity=AlertSeverity.critical,
            evidence_image_path=evidence_image_path,
            metadata=metadata,
        )

        # Create alert via standard service (no rule_id, no roi_id).
        alert = AlertService.create_alert(candidate, db)

        # Immediately publish an escalated event to trigger notifications.
        escalated_event = AlertEvent(
            event_type=AlertEventType.escalated,
            alert_id=alert.id,
            camera_id=alert.camera_id,
            severity=alert.severity,
            metadata={
                "reason": "fire_smoke_detection",
                "detection_labels": list({d.label for d in detections}),
            },
        )
        event_bus.publish(escalated_event)

        logger.critical(
            "Critical fire/smoke alert created — alert_id=%d camera_id=%d",
            alert.id,
            camera_id,
        )

        return alert
