"""Debris / litter detector — YOLO-based floor-zone anomaly detection.

Detects debris-like objects (trash, bottles, bags, boxes, etc.) inside
configured floor-zone ROIs.  Uses Ultralytics YOLO for inference and the
shared :class:`BaseDetector` contract for platform integration.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon

from backend.app.detectors.base import BaseDetector, DetectionResult
from shared.coordinate_standard import Point

logger = logging.getLogger(__name__)

# Default YOLO class names commonly associated with debris / litter.
DEFAULT_DEBRIS_CLASSES: list[str] = [
    "bottle",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "bench",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "trash",
    "litter",
    "debris",
    "box",
    "bag",
    "package",
]

DEFAULT_MODEL_PATH = "yolov8n.pt"


def _bbox_to_polygon(x1: float, y1: float, x2: float, y2: float) -> list[Point]:
    """Convert normalised axis-aligned bbox to a 4-point polygon."""
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def _centroid(polygon: list[Point]) -> Point:
    """Return the centroid of a polygon (simple average of vertices)."""
    n = len(polygon)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    return (cx, cy)


class DebrisDetector(BaseDetector):
    """YOLO-based debris / litter detector for floor zones.

    Args:
        model_path: Path to YOLO weights file.  If the file does not exist
            the detector self-disables and returns empty results.
        debris_classes: YOLO class names to treat as debris.  Defaults to
            :data:`DEFAULT_DEBRIS_CLASSES`.
        min_confidence: Minimum detection confidence to keep.
        min_area_ratio: Minimum bbox-area / ROI-area ratio to report.
        enabled: Initial enabled state.
    """

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        debris_classes: list[str] | None = None,
        min_confidence: float = 0.35,
        min_area_ratio: float = 0.005,
        enabled: bool = True,
    ) -> None:
        self._model_path = Path(model_path)
        self._debris_classes = set(debris_classes or DEFAULT_DEBRIS_CLASSES)
        self._min_confidence = min_confidence
        self._min_area_ratio = min_area_ratio
        self._enabled = enabled
        self._model: Any = None
        self._model_loaded = False

    # ------------------------------------------------------------------
    # BaseDetector interface
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def detect(
        self,
        image_bytes: bytes,
        roi_polygons: list[list[Point]],
        config: dict[str, Any],
    ) -> list[DetectionResult]:
        """Run YOLO detection filtered to floor-zone ROIs.

        If the YOLO model weights are unavailable the detector logs a
        warning and returns an empty list.
        """
        if not self._enabled:
            return []

        model = self._get_model()
        if model is None:
            return []

        # Apply runtime config overrides
        debris_classes = set(config.get("debris_classes", self._debris_classes))
        min_confidence = float(config.get("min_confidence", self._min_confidence))
        min_area_ratio = float(config.get("min_area_ratio", self._min_area_ratio))

        # Decode image
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception:
            logger.warning("DebrisDetector: failed to decode image bytes")
            return []

        img_w, img_h = image.size

        # Run YOLO inference
        try:
            results = model(np.array(image), verbose=False)
        except Exception:
            logger.exception("DebrisDetector: YOLO inference failed")
            return []

        if not roi_polygons:
            # No ROI filter — return nothing (floor-zone-only detector)
            return []

        # Pre-compute Shapely polygons for ROIs
        roi_shapes: list[ShapelyPolygon] = []
        for rp in roi_polygons:
            if len(rp) >= 3:
                roi_shapes.append(ShapelyPolygon(rp))

        if not roi_shapes:
            return []

        detections: list[DetectionResult] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                conf = float(box.conf[0])
                if conf < min_confidence:
                    continue

                cls_id = int(box.cls[0])
                class_name = model.names.get(cls_id, "")
                if class_name not in debris_classes:
                    continue

                # Normalise bbox to [0, 1]
                x1 = float(box.xyxy[0][0]) / img_w
                y1 = float(box.xyxy[0][1]) / img_h
                x2 = float(box.xyxy[0][2]) / img_w
                y2 = float(box.xyxy[0][3]) / img_h

                # Clamp to valid range
                x1 = max(0.0, min(1.0, x1))
                y1 = max(0.0, min(1.0, y1))
                x2 = max(0.0, min(1.0, x2))
                y2 = max(0.0, min(1.0, y2))

                det_polygon = _bbox_to_polygon(x1, y1, x2, y2)
                centroid = _centroid(det_polygon)

                # Check centroid falls inside at least one ROI
                inside_roi = False
                best_roi_area = 0.0
                for roi_shape in roi_shapes:
                    if roi_shape.contains(ShapelyPoint(centroid)):
                        inside_roi = True
                        # Compute area ratio of detection vs this ROI
                        det_shape = ShapelyPolygon(det_polygon)
                        if roi_shape.area > 0:
                            area_ratio = float(
                                det_shape.intersection(roi_shape).area
                                / roi_shape.area
                            )
                            if area_ratio > best_roi_area:
                                best_roi_area = area_ratio
                        break

                if not inside_roi:
                    continue

                if best_roi_area < min_area_ratio:
                    continue

                detections.append(
                    DetectionResult(
                        polygon=det_polygon,
                        confidence=conf,
                        label=class_name,
                        metadata={
                            "class_id": cls_id,
                            "area_ratio": best_roi_area,
                        },
                    )
                )

        return detections

    # ------------------------------------------------------------------
    # Model loading (lazy)
    # ------------------------------------------------------------------

    def _get_model(self) -> Any:
        """Lazily load and cache the YOLO model.

        Returns ``None`` if weights are missing.
        """
        if self._model_loaded:
            return self._model

        self._model_loaded = True  # only try once

        if not self._model_path.exists():
            logger.warning(
                "DebrisDetector: model weights not found at %s — "
                "detector disabled",
                self._model_path,
            )
            return None

        try:
            from ultralytics import YOLO

            self._model = YOLO(str(self._model_path))
            logger.info("DebrisDetector: loaded YOLO model from %s", self._model_path)
            return self._model
        except ImportError:
            logger.warning(
                "DebrisDetector: ultralytics package not installed — "
                "detector disabled"
            )
            return None
        except Exception:
            logger.exception("DebrisDetector: failed to load YOLO model")
            return None
