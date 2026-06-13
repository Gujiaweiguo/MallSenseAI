from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.api.utils import Camera, Scene, commit_refresh, ensure_exists, get_or_404, paginate, select, set_if_provided
from backend.app.camera.adapter import CameraCaptureError, DahuaCameraAdapter
from backend.app.db.session import get_db
from backend.app.models import UserRole
from backend.app.schemas.scene import SceneCreate, SceneResponse, SceneUpdate

router = APIRouter(prefix="/scenes", tags=["scenes"], dependencies=[Depends(get_current_user)])
BASELINE_DIR = Path("data/baselines")


@router.get("", response_model=list[SceneResponse])
def list_scenes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Scene]:
    return paginate(select(Scene).order_by(Scene.id), db, skip, limit)


@router.get("/{scene_id}", response_model=SceneResponse)
def get_scene(scene_id: int, db: Session = Depends(get_db)) -> Scene:
    return get_or_404(db, Scene, scene_id)


@router.post("", response_model=SceneResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.operator))])
def create_scene(payload: SceneCreate, db: Session = Depends(get_db)) -> Scene:
    ensure_exists(db, Camera, payload.camera_id)
    scene = Scene(**payload.model_dump())
    db.add(scene)
    return commit_refresh(db, scene)


@router.put("/{scene_id}", response_model=SceneResponse, dependencies=[Depends(require_role(UserRole.operator))])
def update_scene(scene_id: int, payload: SceneUpdate, db: Session = Depends(get_db)) -> Scene:
    scene = get_or_404(db, Scene, scene_id)
    data = payload.model_dump(exclude_unset=True)
    ensure_exists(db, Camera, data.get("camera_id"))
    set_if_provided(scene, data)
    return commit_refresh(db, scene)


@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.operator))])
def delete_scene(scene_id: int, db: Session = Depends(get_db)) -> None:
    scene = get_or_404(db, Scene, scene_id)
    db.delete(scene)
    db.commit()


@router.put("/{scene_id}/baseline", response_model=SceneResponse, dependencies=[Depends(require_role(UserRole.operator))])
def upload_baseline(scene_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)) -> Scene:
    scene = get_or_404(db, Scene, scene_id)
    suffix = Path(file.filename or "baseline.jpg").suffix or ".jpg"
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    target = BASELINE_DIR / f"scene_{scene_id}{suffix}"
    with target.open("wb") as output:
        output.write(file.file.read())
    scene.baseline_image_path = str(target)
    return commit_refresh(db, scene)


@router.get("/{scene_id}/baseline")
def get_baseline(scene_id: int, db: Session = Depends(get_db)) -> FileResponse:
    scene = get_or_404(db, Scene, scene_id)
    if not scene.baseline_image_path or not Path(scene.baseline_image_path).exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Baseline image not found")
    return FileResponse(scene.baseline_image_path)


@router.post("/{scene_id}/snapshot", response_model=SceneResponse, dependencies=[Depends(require_role(UserRole.operator))])
async def capture_scene_snapshot(scene_id: int, db: Session = Depends(get_db)) -> Scene:
    scene = get_or_404(db, Scene, scene_id)
    camera = get_or_404(db, Camera, scene.camera_id)

    adapter = DahuaCameraAdapter(
        ip=camera.ip,
        port=camera.port,
        username=camera.username or "admin",
        password=camera.password_hash,
        timeout=15.0,
    )

    try:
        image_bytes = await adapter.capture_snapshot()
    except CameraCaptureError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Camera capture failed")

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    target = BASELINE_DIR / f"scene_{scene_id}.jpg"
    target.write_bytes(image_bytes)
    scene.baseline_image_path = str(target)
    return commit_refresh(db, scene)
