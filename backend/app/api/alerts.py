from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.api.utils import Alert, commit_refresh, get_or_404, mark_alert_resolution, paginate, select
from backend.app.db.session import get_db
from backend.app.models import AlertSeverity, AlertStatus, UserRole
from backend.app.schemas.alert import AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AlertResponse])
def list_alerts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Alert]:
    return paginate(select(Alert).order_by(Alert.detected_at.desc()), db, skip, limit)


@router.get("/export")
def export_alerts(
    severity: AlertSeverity | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    stmt = select(Alert).order_by(Alert.detected_at.desc())
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    rows = list(db.scalars(stmt).all())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "camera_id", "alert_type", "severity", "status", "detected_at", "resolved_at"])
    for a in rows:
        writer.writerow([
            a.id,
            a.camera_id,
            a.alert_type.value,
            a.severity.value,
            a.status.value,
            a.detected_at.isoformat() if a.detected_at else "",
            a.resolved_at.isoformat() if a.resolved_at else "",
        ])
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts.csv"},
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    return get_or_404(db, Alert, alert_id)


@router.get("/{alert_id}/evidence")
def get_alert_evidence(alert_id: int, db: Session = Depends(get_db)) -> FileResponse:
    alert = get_or_404(db, Alert, alert_id)
    if not alert.evidence_image_path or not Path(alert.evidence_image_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence image not found")
    return FileResponse(alert.evidence_image_path)


@router.put("/{alert_id}", response_model=AlertResponse, dependencies=[Depends(require_role(UserRole.admin))])
def update_alert_status(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)) -> Alert:
    alert = get_or_404(db, Alert, alert_id)
    alert.status = payload.status
    mark_alert_resolution(alert)
    return commit_refresh(db, alert)
