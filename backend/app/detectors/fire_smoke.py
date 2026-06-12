"""Fire and smoke detector using YOLO."""

from __future__ import annotations

import io
import logging
from typing import Any

from backend.app.detectors.base import BaseDetector, DetectionResult
from shared.coordinate_standard import Point

logger = logging.getLogger(__name__)

_FIRE_SMOKE_LABELS: frozenset[str] = frozenset({"fire", "smoke", "flame"})
_DEFAULT_MODEL_PATH = "yolov8n.pt"


class FireSmokeDetector(BaseDetector):
    """Detect fire, smoke and flame via YOLO.

    Every detection is tagged as *critical* severity.  Controlled by the
    ``fire_smoke_enabled`` feature-flag.
    """

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.5,
        min_area_ratio: float = 0.01,
        model_path: str = _DEFAULT_MODEL_PATH,
        enabled: bool = True,
    ) -> None:
        super().__init__()
        self._confidence_threshold = confidence_threshold
        self._min_area_ratio = min_area_ratio
        self._model_path = model_path
        self._enabled = enabled
        self._model: Any | None = None

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def detect(
        self,
        image_bytes: bytes,
        roi_polygons: list[list[Point]],
        config: dict[str, Any],
    ) -> list[DetectionResult]:
        if not self._enabled:
            return []

        model = self._load_model()
        if model is None:
            return []

        confidence_threshold = config.get("confidence_threshold", self._confidence_threshold)
        min_area_ratio = config.get("min_area_ratio", self._min_area_ratio)

        try:
            from PIL import Image  # type: ignore[import-untyped]
            import numpy as np

            img = Image.open(io.BytesIO(image_bytes))
            frame = np.array(img)
        except Exception:
            logger.exception("Failed to decode image bytes for fire/smoke detection")
            return []

        img_h, img_w = frame.shape[:2]
        if img_h == 0 or img_w == 0:
            return []
        total_area = float(img_h * img_w)

        try:
            predictions = model(frame, verbose=False)
        except Exception:
            logger.exception("YOLO inference failed for fire/smoke detection")
            return []

        results: list[DetectionResult] = []

        for pred in predictions:
            boxes = getattr(pred, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if conf < confidence_threshold:
                    continue

                label = (
                    model.names.get(cls_id, str(cls_id))
                    if hasattr(model, "names")
                    else str(cls_id)
                )
                if label.lower() not in _FIRE_SMOKE_LABELS:
                    continue

                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = (
                    float(xyxy[0]),
                    float(xyxy[1]),
                    float(xyxy[2]),
                    float(xyxy[3]),
                )
                bbox_area = (x2 - x1) * (y2 - y1)
                area_ratio = bbox_area / total_area
                if area_ratio < min_area_ratio:
                    continue

                # Convert pixel bbox to normalised polygon: (x1,y1),(x2,y1),(x2,y2),(x1,y2)
                nx1, ny1 = x1 / img_w, y1 / img_h
                nx2, ny2 = x2 / img_w, y2 / img_h
                polygon: list[Point] = [
                    (nx1, ny1),
                    (nx2, ny1),
                    (nx2, ny2),
                    (nx1, ny2),
                ]

                # Skip if ROI polygons provided and detection is outside all of them
                if roi_polygons and not _inside_any_roi(polygon, roi_polygons):
                    continue

                results.append(
                    DetectionResult(
                        polygon=polygon,
                        confidence=conf,
                        label=label,
                        metadata={"severity": "critical", "category": "fire_smoke", "area_ratio": area_ratio},
                    )
                )

        return results

    def _load_model(self) -> Any | None:
        if self._model is not None:
            return self._model

        try:
            from ultralytics import YOLO  # type: ignore[import-untyped]

            self._model = YOLO(self._model_path)
            return self._model
        except Exception:
            logger.warning(
                "Could not load YOLO model from %s — fire/smoke detection disabled",
                self._model_path,
                exc_info=True,
            )
            return None


def _inside_any_roi(polygon: list[Point], roi_polygons: list[list[Point]]) -> bool:
    """Check if the detection polygon centre falls inside any ROI polygon."""
    cx = sum(p[0] for p in polygon) / len(polygon)
    cy = sum(p[1] for p in polygon) / len(polygon)
    for roi in roi_polygons:
        if _point_in_polygon(cx, cy, roi):
            return True
    return False


def _point_in_polygon(px: float, py: float, polygon: list[Point]) -> bool:
    """Ray-casting algorithm for point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside
