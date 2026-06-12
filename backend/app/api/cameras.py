from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.auth.password import hash_password
from backend.app.api.utils import Camera, commit_refresh, get_or_404, paginate, select, set_if_provided
from backend.app.db.session import get_db
from backend.app.models import UserRole
from backend.app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate

router = APIRouter(prefix="/cameras", tags=["cameras"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CameraResponse])
def list_cameras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Camera]:
    return paginate(select(Camera).order_by(Camera.id), db, skip, limit)


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: int, db: Session = Depends(get_db)) -> Camera:
    return get_or_404(db, Camera, camera_id)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.operator))])
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)) -> Camera:
    data = payload.model_dump(exclude={"password"})
    camera = Camera(**data, password_hash=hash_password(payload.password))
    db.add(camera)
    return commit_refresh(db, camera)


@router.put("/{camera_id}", response_model=CameraResponse, dependencies=[Depends(require_role(UserRole.operator))])
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)) -> Camera:
    camera = get_or_404(db, Camera, camera_id)
    data = payload.model_dump(exclude_unset=True, exclude={"password"})
    set_if_provided(camera, data)
    if payload.password is not None:
        camera.password_hash = hash_password(payload.password)
    return commit_refresh(db, camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.operator))])
def delete_camera(camera_id: int, db: Session = Depends(get_db)) -> None:
    camera = get_or_404(db, Camera, camera_id)
    db.delete(camera)
    db.commit()


@router.post("/{camera_id}/snapshot", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_role(UserRole.operator))])
def trigger_snapshot(camera_id: int, db: Session = Depends(get_db)) -> dict[str, str | int]:
    get_or_404(db, Camera, camera_id)
    return {"camera_id": camera_id, "status": "accepted"}
