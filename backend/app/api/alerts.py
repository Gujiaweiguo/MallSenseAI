from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.api.utils import Alert, commit_refresh, get_or_404, mark_alert_resolution, paginate, select
from backend.app.db.session import get_db
from backend.app.models import UserRole
from backend.app.schemas.alert import AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AlertResponse])
def list_alerts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Alert]:
    return paginate(select(Alert).order_by(Alert.detected_at.desc()), db, skip, limit)


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    return get_or_404(db, Alert, alert_id)


@router.put("/{alert_id}", response_model=AlertResponse, dependencies=[Depends(require_role(UserRole.admin))])
def update_alert_status(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)) -> Alert:
    alert = get_or_404(db, Alert, alert_id)
    alert.status = payload.status
    mark_alert_resolution(alert)
    return commit_refresh(db, alert)
