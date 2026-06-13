"""Unit tests for workers.pipeline.DetectionPipeline."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.models.entities import AlertSeverity, RuleType
from backend.app.detectors.base import DetectionResult
from backend.app.rules.models import AlertCandidate as RuleAlertCandidate
from backend.app.rules.engine import ActiveRule
from backend.tests.test_pipeline_mocks import (
    make_inspection_result,
    make_detection_result,
    make_rule_candidate,
    FakeDetector,
    FakeDetectorRegistry,
    FakeCooldownTracker,
)
from workers.context import CameraDetectionContext, CameraContextCache, RoiContext
from workers.pipeline import DetectionPipeline, PipelineOutcome


# ---------------------------------------------------------------------------
# process_inspection — capture failure / no image
# ---------------------------------------------------------------------------

class TestProcessInspectionCaptureFailed:
    def test_returns_skipped_when_capture_failed(self):
        pipeline = DetectionPipeline(
            detector_registry=FakeDetectorRegistry(),
            cooldown_tracker=FakeCooldownTracker(),
        )
        result = make_inspection_result(success=False, image_bytes=None)

        import asyncio
        outcome = asyncio.get_event_loop().run_until_complete(
            pipeline.process_inspection(result)
        )

        assert outcome.skipped_reason == "capture_failed"
        assert outcome.alerts_created == 0


# ---------------------------------------------------------------------------
# process_inspection — no detections
# ---------------------------------------------------------------------------

class TestProcessInspectionNoDetections:
    def test_returns_zero_alerts_when_no_detections(self):
        registry = FakeDetectorRegistry()
        pipeline = DetectionPipeline(
            detector_registry=registry,
            cooldown_tracker=FakeCooldownTracker(),
        )
        result = make_inspection_result()

        import asyncio
        outcome = asyncio.get_event_loop().run_until_complete(
            pipeline.process_inspection(result)
        )

        assert outcome.alerts_created == 0
        assert outcome.obstruction_detections == 0
        assert outcome.fire_smoke_detections == 0


# ---------------------------------------------------------------------------
# process_inspection — fire/smoke detection path
# ---------------------------------------------------------------------------

class TestProcessInspectionFireSmoke:
    @patch("workers.pipeline.SessionLocal")
    @patch("workers.pipeline.load_camera_context")
    @patch("workers.pipeline.CriticalAlertHandler")
    def test_creates_critical_alert_on_fire_smoke(self, mock_handler, mock_load, mock_session_cls):
        fire_detection = make_detection_result(label="fire", confidence=0.9)

        registry = FakeDetectorRegistry()
        registry.register("fire_smoke", FakeDetector([fire_detection]))

        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_load.return_value = CameraDetectionContext(
            camera_id=1, rois=[], active_rules=[],
            fire_smoke_config={"confidence_threshold": 0.5},
        )

        mock_handler.handle_fire_smoke_detection.return_value = MagicMock(id=42)

        pipeline = DetectionPipeline(
            detector_registry=registry,
            cooldown_tracker=FakeCooldownTracker(),
        )
        result = make_inspection_result()

        import asyncio
        outcome = asyncio.get_event_loop().run_until_complete(
            pipeline.process_inspection(result)
        )

        assert outcome.fire_smoke_detections == 1
        assert outcome.alerts_created == 1
        mock_handler.handle_fire_smoke_detection.assert_called_once()


# ---------------------------------------------------------------------------
# process_inspection — obstruction detection + rule evaluation
# ---------------------------------------------------------------------------

class TestProcessInspectionObstruction:
    @patch("workers.pipeline.AlertService")
    @patch("workers.pipeline.ObstructionRuleEngine")
    @patch("workers.pipeline.SessionLocal")
    @patch("workers.pipeline.load_camera_context")
    def test_creates_alert_from_rule_candidate(
        self, mock_load, mock_session_cls, mock_engine, mock_alert_svc
    ):
        debris_detection = make_detection_result(label="bottle", confidence=0.8)

        registry = FakeDetectorRegistry()
        registry.register("debris", FakeDetector([debris_detection]))

        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        rule_candidate = make_rule_candidate(camera_id=1, roi_id=10, rule_id=5)
        mock_engine.evaluate.return_value = [rule_candidate]

        active_rule = ActiveRule(
            rule_id=5, camera_id=1, roi_id=10,
            roi_geometry=[], rule_type=RuleType.obstruction_duration,
            config={}, priority=100,
        )
        mock_load.return_value = CameraDetectionContext(
            camera_id=1, rois=[RoiContext(roi_id=10, polygon=[(0.1, 0.1), (0.5, 0.1), (0.5, 0.5), (0.1, 0.5)])],
            active_rules=[active_rule],
        )

        pipeline = DetectionPipeline(
            detector_registry=registry,
            cooldown_tracker=FakeCooldownTracker(),
        )
        result = make_inspection_result()

        import asyncio
        outcome = asyncio.get_event_loop().run_until_complete(
            pipeline.process_inspection(result)
        )

        assert outcome.obstruction_detections == 1
        assert outcome.alerts_created == 1
        mock_alert_svc.create_alert.assert_called_once()


# ---------------------------------------------------------------------------
# CameraContextCache
# ---------------------------------------------------------------------------

class TestCameraContextCache:
    def test_miss_returns_none(self):
        cache = CameraContextCache(ttl_seconds=60.0)
        assert cache.get(999) is None

    def test_hit_returns_context(self):
        cache = CameraContextCache(ttl_seconds=60.0)
        ctx = CameraDetectionContext(camera_id=1, rois=[], active_rules=[])
        cache.set(ctx)
        assert cache.get(1) is ctx

    def test_invalidate_removes_entry(self):
        cache = CameraContextCache(ttl_seconds=60.0)
        ctx = CameraDetectionContext(camera_id=1, rois=[], active_rules=[])
        cache.set(ctx)
        cache.invalidate(1)
        assert cache.get(1) is None

    def test_expired_entry_returns_none(self):
        cache = CameraContextCache(ttl_seconds=0.0)
        ctx = CameraDetectionContext(camera_id=1, rois=[], active_rules=[])
        cache.set(ctx)
        import time
        time.sleep(0.01)
        assert cache.get(1) is None


# ---------------------------------------------------------------------------
# _convert_rule_candidate
# ---------------------------------------------------------------------------

class TestConvertRuleCandidate:
    def test_maps_fields_correctly(self):
        from workers.pipeline import DetectionPipeline as DP

        rule_candidate = RuleAlertCandidate(
            camera_id=1,
            roi_id=10,
            rule_id=5,
            rule_type=RuleType.obstruction_duration,
            severity=AlertSeverity.high,
            evidence={"zone_polygon": [], "metric_value": 0.8},
            detected_at=datetime.now(timezone.utc),
        )

        result = DP._convert_candidate(rule_candidate, "/path/to/evidence.jpg")

        assert result.camera_id == 1
        assert result.roi_id == 10
        assert result.rule_id == 5
        assert result.alert_type == RuleType.obstruction_duration
        assert result.severity == AlertSeverity.high
        assert result.evidence_image_path == "/path/to/evidence.jpg"
        assert result.metadata == {"zone_polygon": [], "metric_value": 0.8}
