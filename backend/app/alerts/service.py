from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.alerts.events import AlertEvent, AlertEventType, event_bus
from backend.app.alerts.state_machine import get_open_work_order_for_alert
from backend.app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    RuleType,
    WorkOrder,
    WorkOrderStatus,
)


@dataclass
class AlertCandidate:
    """Lightweight input produced by the rule engine, consumed by AlertService."""

    camera_id: int
    roi_id: int | None = None
    rule_id: int | None = None
    alert_type: RuleType = RuleType.obstruction_duration
    severity: AlertSeverity = AlertSeverity.medium
    evidence_image_path: str | None = None
    metadata: dict[str, Any] | None = None


class InvalidAlertTransition(Exception):
    """Raised when an alert status transition is not allowed."""

    def __init__(self, current: AlertStatus, target: AlertStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid alert transition: {current.value} -> {target.value}"
        )


# Allowed alert status transitions
_ALERT_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.pending: {AlertStatus.confirmed, AlertStatus.false_positive},
    AlertStatus.confirmed: {AlertStatus.resolved, AlertStatus.false_positive},
    # Terminal
    AlertStatus.resolved: set(),
    AlertStatus.false_positive: set(),
}


def _validate_alert_transition(
    current: AlertStatus, target: AlertStatus
) -> None:
    allowed = _ALERT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidAlertTransition(current, target)


def _emit(
    event_type: AlertEventType, alert: Alert, extra: dict[str, Any] | None = None
) -> None:
    event = AlertEvent(
        event_type=event_type,
        alert_id=alert.id,
        camera_id=alert.camera_id,
        severity=alert.severity,
        metadata=extra or {},
    )
    event_bus.publish(event)


class AlertService:
    """Creates alerts from detection events and manages their lifecycle."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    @staticmethod
    def create_alert(candidate: AlertCandidate, db: Session) -> Alert:
        """Persist a new Alert from a rule-engine AlertCandidate."""
        alert = Alert(
            camera_id=candidate.camera_id,
            roi_id=candidate.roi_id,
            rule_id=candidate.rule_id,
            alert_type=candidate.alert_type,
            severity=candidate.severity,
            evidence_image_path=candidate.evidence_image_path,
            status=AlertStatus.pending,
            detected_at=datetime.now(timezone.utc),
            event_metadata=candidate.metadata or {},
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        _emit(AlertEventType.created, alert)
        return alert

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    @staticmethod
    def confirm_alert(alert_id: int, db: Session) -> Alert:
        """Transition alert to confirmed and auto-create a work order."""
        alert = _get_alert_or_raise(db, alert_id)
        _validate_alert_transition(alert.status, AlertStatus.confirmed)
        alert.status = AlertStatus.confirmed
        db.commit()
        db.refresh(alert)
        _emit(AlertEventType.confirmed, alert)
        # Auto-create work order
        AlertService.auto_create_work_order(alert, db)
        return alert

    @staticmethod
    def mark_false_positive(
        alert_id: int, db: Session, reason: str = ""
    ) -> Alert:
        """Transition alert to false_positive."""
        alert = _get_alert_or_raise(db, alert_id)
        _validate_alert_transition(alert.status, AlertStatus.false_positive)
        alert.status = AlertStatus.false_positive
        meta = dict(alert.event_metadata)
        if reason:
            meta["false_positive_reason"] = reason
            alert.event_metadata = meta
        db.commit()
        db.refresh(alert)
        _emit(AlertEventType.false_positive, alert, {"reason": reason})
        return alert

    @staticmethod
    def resolve_alert(
        alert_id: int, db: Session, notes: str = ""
    ) -> Alert:
        """Transition alert to resolved and set resolved_at."""
        alert = _get_alert_or_raise(db, alert_id)
        _validate_alert_transition(alert.status, AlertStatus.resolved)
        alert.status = AlertStatus.resolved
        alert.resolved_at = datetime.now(timezone.utc)
        if notes:
            meta = dict(alert.event_metadata)
            meta["resolution_notes"] = notes
            alert.event_metadata = meta
        db.commit()
        db.refresh(alert)
        _emit(AlertEventType.resolved, alert, {"notes": notes})
        return alert

    # ------------------------------------------------------------------
    # Work-order helpers
    # ------------------------------------------------------------------

    @staticmethod
    def auto_create_work_order(
        alert: Alert, db: Session
    ) -> WorkOrder | None:
        """Create an open WorkOrder for a confirmed alert (if none exists)."""
        existing = get_open_work_order_for_alert(alert.id, db)
        if existing is not None:
            return None
        work_order = WorkOrder(
            alert_id=alert.id,
            status=WorkOrderStatus.open,
        )
        db.add(work_order)
        db.commit()
        db.refresh(work_order)
        return work_order

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @staticmethod
    def get_active_alerts(
        camera_id: int | None, db: Session
    ) -> list[Alert]:
        """Return pending and confirmed alerts, optionally filtered by camera."""
        stmt = (
            select(Alert)
            .where(
                Alert.status.in_(
                    [AlertStatus.pending, AlertStatus.confirmed]
                )
            )
            .order_by(Alert.detected_at.desc())
        )
        if camera_id is not None:
            stmt = stmt.where(Alert.camera_id == camera_id)
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_alert_history(
        camera_id: int, limit: int, db: Session
    ) -> list[Alert]:
        """Return paginated alert history for a camera."""
        stmt = (
            select(Alert)
            .where(Alert.camera_id == camera_id)
            .order_by(Alert.detected_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt).all())


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _get_alert_or_raise(db: Session, alert_id: int) -> Alert:
    from fastapi import HTTPException, status

    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return alert
