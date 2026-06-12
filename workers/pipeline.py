"""Detection pipeline — capture → detect → evaluate rules → create alerts."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.app.alerts.critical import CriticalAlertHandler
from backend.app.alerts.service import AlertCandidate as ServiceAlertCandidate
from backend.app.alerts.service import AlertService
from backend.app.db.session import SessionLocal
from backend.app.detectors.base import DetectionResult
from backend.app.detectors.integration import DetectorRegistry
from backend.app.models.entities import RuleType
from backend.app.rules.cooldown import CooldownTracker
from backend.app.rules.engine import ObstructionRuleEngine
from backend.app.rules.models import AlertCandidate as RuleAlertCandidate
from workers.context import CameraContextCache, CameraDetectionContext, load_camera_context
from workers.models import InspectionResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineOutcome:
    camera_id: int
    obstruction_detections: int = 0
    fire_smoke_detections: int = 0
    alerts_created: int = 0
    skipped_reason: str | None = None


class DetectionPipeline:
    """Orchestrates: load context → run detectors → evaluate rules → create alerts."""

    def __init__(
        self,
        detector_registry: DetectorRegistry,
        cooldown_tracker: CooldownTracker,
        context_cache: CameraContextCache | None = None,
        evidence_root: str = "data/assets/cameras",
    ) -> None:
        self._registry = detector_registry
        self._cooldown = cooldown_tracker
        self._cache = context_cache or CameraContextCache()
        self._evidence_root = Path(evidence_root)
        self._cooldown_state: dict[int, float] = {}

    async def process_inspection(self, inspection: InspectionResult) -> PipelineOutcome:
        if not inspection.success or not inspection.image_bytes:
            return PipelineOutcome(
                camera_id=inspection.camera_id,
                skipped_reason="capture_failed",
            )

        try:
            with SessionLocal() as db:
                return await self._process(inspection, db)
        except Exception:
            logger.exception("Pipeline error for camera %d", inspection.camera_id)
            return PipelineOutcome(
                camera_id=inspection.camera_id,
                skipped_reason="pipeline_error",
            )

    async def _process(
        self, inspection: InspectionResult, db: Session
    ) -> PipelineOutcome:
        assert inspection.image_bytes is not None  # guaranteed by process_inspection guard
        image_bytes: bytes = inspection.image_bytes

        context = self._cache.get(inspection.camera_id)
        if context is None:
            context = load_camera_context(inspection.camera_id, db)
            self._cache.set(context)

        obstruction = await self._run_obstruction(image_bytes, context)
        fire_smoke = await self._run_fire_smoke(image_bytes)

        evidence_path: str | None = None
        if obstruction or fire_smoke:
            evidence_path = self._save_evidence(
                inspection.camera_id, inspection.timestamp, image_bytes
            )

        alerts_created = 0

        if fire_smoke:
            try:
                alert = CriticalAlertHandler.handle_fire_smoke_detection(
                    camera_id=inspection.camera_id,
                    detections=fire_smoke,
                    db=db,
                    evidence_image_path=evidence_path,
                )
                if alert:
                    alerts_created += 1
            except Exception:
                logger.exception("Fire/smoke alert creation failed for camera %d", inspection.camera_id)

        if obstruction and context.active_rules:
            try:
                candidates = self._evaluate_rules(inspection.camera_id, obstruction, context)
                for candidate in candidates:
                    service_candidate = self._convert_candidate(candidate, evidence_path)
                    AlertService.create_alert(service_candidate, db)
                    alerts_created += 1
            except Exception:
                logger.exception("Obstruction alert creation failed for camera %d", inspection.camera_id)

        return PipelineOutcome(
            camera_id=inspection.camera_id,
            obstruction_detections=len(obstruction),
            fire_smoke_detections=len(fire_smoke),
            alerts_created=alerts_created,
        )

    async def _run_obstruction(
        self, image_bytes: bytes, context: CameraDetectionContext
    ) -> list[DetectionResult]:
        detector = self._registry.get_detector("debris")
        if detector is None or not detector.is_enabled:
            return []
        roi_polygons = [r.polygon for r in context.rois]
        if not roi_polygons:
            return []
        try:
            return await detector.detect(image_bytes, roi_polygons, {})
        except Exception:
            logger.exception("Obstruction detector error")
            return []

    async def _run_fire_smoke(self, image_bytes: bytes) -> list[DetectionResult]:
        detector = self._registry.get_detector("fire_smoke")
        if detector is None or not detector.is_enabled:
            return []
        try:
            return await detector.detect(image_bytes, [], {})
        except Exception:
            logger.exception("Fire/smoke detector error")
            return []

    def _evaluate_rules(
        self,
        camera_id: int,
        detections: list[DetectionResult],
        context: CameraDetectionContext,
    ) -> list[RuleAlertCandidate]:
        detection_polygons = [d.polygon for d in detections]
        candidates = ObstructionRuleEngine.evaluate(
            camera_id=camera_id,
            detection_polygons=detection_polygons,
            active_rules=context.active_rules,
            cooldown_state=self._cooldown_state,
        )
        # Update cooldown state for triggered rules
        for candidate in candidates:
            key = candidate.rule_id
            self._cooldown_state[key] = time.time()
        return candidates

    @staticmethod
    def _convert_candidate(
        candidate: RuleAlertCandidate, evidence_image_path: str | None
    ) -> ServiceAlertCandidate:
        return ServiceAlertCandidate(
            camera_id=candidate.camera_id,
            roi_id=candidate.roi_id,
            rule_id=candidate.rule_id,
            alert_type=candidate.rule_type if isinstance(candidate.rule_type, RuleType) else RuleType.obstruction_duration,
            severity=candidate.severity,
            evidence_image_path=evidence_image_path,
            metadata=candidate.evidence,
        )

    def _save_evidence(
        self, camera_id: int, captured_at: datetime, image_bytes: bytes
    ) -> str:
        ts = captured_at if captured_at.tzinfo else captured_at.replace(tzinfo=timezone.utc)
        path = (
            self._evidence_root
            / str(camera_id)
            / "evidence"
            / f"{ts.year:04d}"
            / f"{ts.month:02d}"
            / f"{ts.day:02d}"
            / f"{ts.strftime('%Y%m%d_%H%M%S')}.jpg"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        return str(path)
