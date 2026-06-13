"""Camera detection context loading and caching."""

import logging
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from typing import Any

from backend.app.models.entities import ROI, Rule, RuleType, Scene
from backend.app.rules.engine import ActiveRule
from shared.coordinate_standard import Geometry, Point, PolygonGeometry, RectGeometry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoiContext:
    roi_id: int
    polygon: list[Point]
    zone_type: str | None = None


@dataclass(frozen=True)
class CameraDetectionContext:
    camera_id: int
    rois: list[RoiContext]
    active_rules: list[ActiveRule]
    fire_smoke_config: dict[str, Any] | None = None


class CameraContextCache:
    """TTL cache for per-camera detection context."""

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[int, tuple[float, CameraDetectionContext]] = {}

    def get(self, camera_id: int) -> CameraDetectionContext | None:
        entry = self._entries.get(camera_id)
        if entry is None:
            return None
        expires_at, context = entry
        if time.monotonic() >= expires_at:
            self._entries.pop(camera_id, None)
            return None
        return context

    def set(self, context: CameraDetectionContext) -> None:
        self._entries[context.camera_id] = (
            time.monotonic() + self._ttl_seconds,
            context,
        )

    def invalidate(self, camera_id: int) -> None:
        self._entries.pop(camera_id, None)


def load_camera_context(camera_id: int, db: Session) -> CameraDetectionContext:
    """Load ROI polygons and active rules for one camera."""
    scene_ids = list(
        db.scalars(
            select(Scene.id).where(Scene.camera_id == camera_id).order_by(Scene.id)
        ).all()
    )

    rois: list[ROI] = []
    if scene_ids:
        rois = list(
            db.scalars(
                select(ROI).where(ROI.scene_id.in_(scene_ids)).order_by(ROI.id)
            ).all()
        )

    roi_by_id: dict[int, ROI] = {roi.id: roi for roi in rois}
    roi_contexts = [
        RoiContext(
            roi_id=roi.id,
            polygon=_geometry_to_polygon(roi.geometry),
            zone_type=getattr(roi.zone_type, "value", roi.zone_type),
        )
        for roi in rois
    ]

    rules = list(
        db.scalars(
            select(Rule)
            .where(Rule.camera_id == camera_id, Rule.enabled.is_(True))
            .order_by(Rule.priority, Rule.id)
        ).all()
    )

    active_rules: list[ActiveRule] = []
    for rule in rules:
        if rule.roi_id is None:
            continue
        roi = roi_by_id.get(rule.roi_id)
        if roi is None:
            logger.debug(
                "Skipping rule %s for camera %s because ROI %s was not found",
                rule.id,
                camera_id,
                rule.roi_id,
            )
            continue
        active_rules.append(
            ActiveRule(
                rule_id=rule.id,
                camera_id=rule.camera_id,
                roi_id=rule.roi_id,
                roi_geometry=_normalize_geometry(roi.geometry),
                rule_type=rule.rule_type,
                config=dict(rule.config or {}),
                priority=rule.priority,
            )
        )

    fire_smoke_rule = next(
        (r for r in rules if r.rule_type == RuleType.fire_smoke),
        None,
    )
    fire_smoke_config: dict[str, Any] | None = (
        dict(fire_smoke_rule.config or {}) if fire_smoke_rule else None
    )

    return CameraDetectionContext(
        camera_id=camera_id,
        rois=roi_contexts,
        active_rules=active_rules,
        fire_smoke_config=fire_smoke_config,
    )


def _geometry_to_polygon(geometry: Geometry | dict[str, object]) -> list[Point]:
    normalized = _normalize_geometry(geometry)
    if normalized["type"] == "polygon":
        return [(float(x), float(y)) for x, y in normalized["points"]]
    x = float(normalized["x"])
    y = float(normalized["y"])
    width = float(normalized["width"])
    height = float(normalized["height"])
    return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]


def _normalize_geometry(geometry: Geometry | dict[str, object]) -> Geometry:
    geometry_type = str(geometry.get("type", ""))
    if geometry_type == "polygon":
        points = [
            (float(point[0]), float(point[1]))
            for point in geometry.get("points", [])
        ]
        polygon: PolygonGeometry = {"type": "polygon", "points": points}
        return polygon
    rect: RectGeometry = {
        "type": "rect",
        "x": float(geometry.get("x", 0.0)),
        "y": float(geometry.get("y", 0.0)),
        "width": float(geometry.get("width", 0.0)),
        "height": float(geometry.get("height", 0.0)),
    }
    return rect
