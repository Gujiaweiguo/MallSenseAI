"""Test helpers and fakes for pipeline unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.detectors.base import BaseDetector, DetectionResult
from backend.app.detectors.integration import DetectorRegistry
from backend.app.rules.cooldown import CooldownTracker
from backend.app.models.entities import AlertSeverity, RuleType
from backend.app.rules.models import AlertCandidate as RuleAlertCandidate
from workers.models import InspectionResult


class FakeDetector(BaseDetector):
    """Returns a fixed list of DetectionResults."""

    def __init__(self, results: list[DetectionResult] | None = None) -> None:
        self._results = results or []

    @property
    def is_enabled(self) -> bool:
        return True

    async def detect(
        self,
        image_bytes: bytes,
        roi_polygons: list[list[tuple[float, float]]],
        config: dict[str, Any],
    ) -> list[DetectionResult]:
        return self._results


class FakeDetectorRegistry(DetectorRegistry):
    """Registry with no detectors by default."""

    def __init__(self) -> None:
        super().__init__()


class FakeCooldownTracker(CooldownTracker):
    """Always reports cooled down."""

    def is_cooled_down(self, rule_id: int, roi_id: int, cooldown_seconds: float) -> bool:
        return True


def make_inspection_result(
    camera_id: int = 1,
    success: bool = True,
    image_bytes: bytes | None = b"\xff\xd8\xff\xe0fake_jpeg_data",
) -> InspectionResult:
    return InspectionResult(
        camera_id=camera_id,
        success=success,
        image_bytes=image_bytes,
        error=None,
        duration_ms=100.0,
        timestamp=datetime.now(timezone.utc),
    )


def make_detection_result(
    label: str = "bottle",
    confidence: float = 0.85,
    polygon: list[tuple[float, float]] | None = None,
) -> DetectionResult:
    return DetectionResult(
        polygon=polygon or [(0.2, 0.2), (0.4, 0.2), (0.4, 0.4), (0.2, 0.4)],
        confidence=confidence,
        label=label,
        metadata={"area_ratio": 0.04, "class_id": 39},
    )


def make_rule_candidate(
    camera_id: int = 1,
    roi_id: int = 10,
    rule_id: int = 5,
    rule_type: RuleType = RuleType.obstruction_duration,
    severity: AlertSeverity = AlertSeverity.medium,
) -> RuleAlertCandidate:
    return RuleAlertCandidate(
        camera_id=camera_id,
        roi_id=roi_id,
        rule_id=rule_id,
        rule_type=rule_type,
        severity=severity,
        evidence={"zone_polygon": [(0.1, 0.1), (0.5, 0.5)], "metric_value": 0.6},
        detected_at=datetime.now(timezone.utc),
    )
