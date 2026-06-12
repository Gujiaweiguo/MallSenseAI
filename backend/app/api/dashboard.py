from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.api.utils import select
from backend.app.auth.dependencies import require_role
from backend.app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    Camera,
    CameraStatus,
    Scene,
    WorkOrder,
    WorkOrderStatus,
)
from backend.app.db.session import get_db

router = APIRouter(tags=["dashboard"])


class DashboardStats(BaseModel):
    cameras_total: int
    cameras_active: int
    cameras_inactive: int
    cameras_error: int
    scenes_total: int
    alerts_total: int
    alerts_pending: int
    alerts_confirmed: int
    alerts_false_positive: int
    alerts_resolved: int
    alerts_by_severity: dict[str, int]
    work_orders_total: int
    work_orders_open: int
    work_orders_in_progress: int
    work_orders_closed: int


@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _user=Depends(require_role("viewer")),
) -> DashboardStats:
    """Aggregate counts from all entity tables for the dashboard overview."""

    # Camera stats
    camera_counts = dict(
        db.execute(
            select(Camera.status, func.count(Camera.id)).group_by(Camera.status)
        ).all()
    )

    # Alert stats
    alert_status_counts = dict(
        db.execute(
            select(Alert.status, func.count(Alert.id)).group_by(Alert.status)
        ).all()
    )
    alert_severity_counts = dict(
        db.execute(
            select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)
        ).all()
    )

    # Work order stats
    wo_status_counts = dict(
        db.execute(
            select(WorkOrder.status, func.count(WorkOrder.id)).group_by(
                WorkOrder.status
            )
        ).all()
    )

    return DashboardStats(
        cameras_total=sum(camera_counts.values()),
        cameras_active=camera_counts.get(CameraStatus.active, 0),
        cameras_inactive=camera_counts.get(CameraStatus.inactive, 0),
        cameras_error=camera_counts.get(CameraStatus.error, 0),
        scenes_total=db.scalar(select(func.count(Scene.id))),
        alerts_total=sum(alert_status_counts.values()),
        alerts_pending=alert_status_counts.get(AlertStatus.pending, 0),
        alerts_confirmed=alert_status_counts.get(AlertStatus.confirmed, 0),
        alerts_false_positive=alert_status_counts.get(AlertStatus.false_positive, 0),
        alerts_resolved=alert_status_counts.get(AlertStatus.resolved, 0),
        alerts_by_severity={str(k): v for k, v in alert_severity_counts.items()},
        work_orders_total=sum(wo_status_counts.values()),
        work_orders_open=wo_status_counts.get(WorkOrderStatus.open, 0),
        work_orders_in_progress=wo_status_counts.get(WorkOrderStatus.in_progress, 0),
        work_orders_closed=wo_status_counts.get(WorkOrderStatus.closed, 0),
    )
