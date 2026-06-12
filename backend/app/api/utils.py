from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Alert, AlertStatus, Camera, ROI, Rule, Scene, User, WorkOrder

ModelT = TypeVar("ModelT")


def paginate(stmt: Any, db: Session, skip: int, limit: int) -> list[Any]:
    return list(db.scalars(stmt.offset(skip).limit(limit)).all())


def get_or_404(db: Session, model: type[ModelT], item_id: int) -> ModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return item


def commit_refresh(db: Session, item: ModelT) -> ModelT:
    db.commit()
    db.refresh(item)
    return item


def ensure_exists(db: Session, model: type[Any], item_id: int | None) -> None:
    if item_id is not None and db.get(model, item_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{model.__name__} not found")


def set_if_provided(item: Any, values: dict[str, Any]) -> None:
    for key, value in values.items():
        setattr(item, key, value)


def mark_alert_resolution(alert: Alert) -> None:
    alert.resolved_at = datetime.now(timezone.utc) if alert.status == AlertStatus.resolved else None


__all__ = [
    "Alert",
    "Camera",
    "ROI",
    "Rule",
    "Scene",
    "User",
    "WorkOrder",
    "commit_refresh",
    "ensure_exists",
    "get_or_404",
    "mark_alert_resolution",
    "paginate",
    "select",
    "set_if_provided",
]
