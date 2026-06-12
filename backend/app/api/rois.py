from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.api.utils import ROI, Scene, commit_refresh, ensure_exists, get_or_404, paginate, select, set_if_provided
from backend.app.db.session import get_db
from backend.app.models import UserRole
from backend.app.schemas.roi import ROICreate, ROIResponse, ROIUpdate

router = APIRouter(prefix="/rois", tags=["rois"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ROIResponse])
def list_rois(skip: int = 0, limit: int = 100, scene_id: int | None = None, db: Session = Depends(get_db)) -> list[ROI]:
    stmt = select(ROI).order_by(ROI.id)
    if scene_id is not None:
        stmt = stmt.where(ROI.scene_id == scene_id)
    return paginate(stmt, db, skip, limit)


@router.get("/{roi_id}", response_model=ROIResponse)
def get_roi(roi_id: int, db: Session = Depends(get_db)) -> ROI:
    return get_or_404(db, ROI, roi_id)


@router.post("", response_model=ROIResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.operator))])
def create_roi(payload: ROICreate, db: Session = Depends(get_db)) -> ROI:
    ensure_exists(db, Scene, payload.scene_id)
    roi = ROI(**payload.model_dump())
    db.add(roi)
    return commit_refresh(db, roi)


@router.put("/{roi_id}", response_model=ROIResponse, dependencies=[Depends(require_role(UserRole.operator))])
def update_roi(roi_id: int, payload: ROIUpdate, db: Session = Depends(get_db)) -> ROI:
    roi = get_or_404(db, ROI, roi_id)
    data = payload.model_dump(exclude_unset=True)
    ensure_exists(db, Scene, data.get("scene_id"))
    set_if_provided(roi, data)
    return commit_refresh(db, roi)


@router.delete("/{roi_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.operator))])
def delete_roi(roi_id: int, db: Session = Depends(get_db)) -> None:
    roi = get_or_404(db, ROI, roi_id)
    db.delete(roi)
    db.commit()
