from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.api.utils import DetectionEvent, get_or_404, paginate, select
from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.schemas.detection_event import DetectionEventResponse

router = APIRouter(
    prefix="/detection-events",
    tags=["detection-events"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[DetectionEventResponse])
def list_detection_events(
    camera_id: int | None = None,
    roi_id: int | None = None,
    detected_after: datetime | None = None,
    detected_before: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[DetectionEvent]:
    stmt = select(DetectionEvent).order_by(DetectionEvent.detected_at.desc())
    if camera_id is not None:
        stmt = stmt.where(DetectionEvent.camera_id == camera_id)
    if roi_id is not None:
        stmt = stmt.where(DetectionEvent.roi_id == roi_id)
    if detected_after is not None:
        stmt = stmt.where(DetectionEvent.detected_at >= detected_after)
    if detected_before is not None:
        stmt = stmt.where(DetectionEvent.detected_at <= detected_before)
    return paginate(stmt, db, skip, limit)


@router.get("/export")
def export_detection_events(
    camera_id: int | None = None,
    roi_id: int | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    stmt = select(DetectionEvent).order_by(DetectionEvent.detected_at.desc())
    if camera_id is not None:
        stmt = stmt.where(DetectionEvent.camera_id == camera_id)
    if roi_id is not None:
        stmt = stmt.where(DetectionEvent.roi_id == roi_id)
    rows = list(db.scalars(stmt).all())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "camera_id", "roi_id", "detector_type", "confidence", "detected_at"])
    for e in rows:
        writer.writerow([
            e.id,
            e.camera_id,
            e.roi_id if e.roi_id is not None else "",
            e.detector_type.value,
            e.confidence if e.confidence is not None else "",
            e.detected_at.isoformat() if e.detected_at else "",
        ])
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=detection_events.csv"},
    )


@router.get("/{event_id}", response_model=DetectionEventResponse)
def get_detection_event(event_id: int, db: Session = Depends(get_db)) -> DetectionEvent:
    return get_or_404(db, DetectionEvent, event_id)
