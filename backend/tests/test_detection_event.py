from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.app.models.entities import DetectorType
from backend.tests.test_pipeline_mocks import make_detection_result
from workers.context import CameraDetectionContext, RoiContext
from workers.pipeline import (
    DetectionPipeline,
    _build_roi_lookup,
    _centroid,
    _match_roi,
    _point_in_polygon,
)


class TestCentroid:
    def test_square_center(self):
        polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        cx, cy = _centroid(polygon)
        assert abs(cx - 0.5) < 1e-9
        assert abs(cy - 0.5) < 1e-9

    def test_empty_polygon(self):
        assert _centroid([]) == (0.0, 0.0)


class TestPointInPolygon:
    def test_inside_square(self):
        polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert _point_in_polygon(0.5, 0.5, polygon) is True

    def test_outside_square(self):
        polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert _point_in_polygon(1.5, 1.5, polygon) is False

    def test_on_edge(self):
        polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        result = _point_in_polygon(0.5, 0.0, polygon)
        assert isinstance(result, bool)


class TestBuildRoiLookup:
    def test_maps_roi_contexts(self):
        ctx = CameraDetectionContext(
            camera_id=1,
            rois=[
                RoiContext(roi_id=10, polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]),
                RoiContext(roi_id=20, polygon=[(0.5, 0.5), (0.9, 0.5), (0.9, 0.9)]),
            ],
            active_rules=[],
        )
        lookup = _build_roi_lookup(ctx)
        assert lookup == {
            10: [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
            20: [(0.5, 0.5), (0.9, 0.5), (0.9, 0.9)],
        }

    def test_empty_rois(self):
        ctx = CameraDetectionContext(camera_id=1, rois=[], active_rules=[])
        assert _build_roi_lookup(ctx) == {}


class TestMatchRoi:
    def test_matches_first_roi(self):
        roi_map = {
            10: [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
            20: [(0.5, 0.5), (0.9, 0.5), (0.9, 0.9), (0.5, 0.9)],
        }
        det = make_detection_result(
            polygon=[(0.1, 0.1), (0.3, 0.1), (0.3, 0.3), (0.1, 0.3)]
        )
        assert _match_roi(det, roi_map) == 10

    def test_no_match_returns_none(self):
        roi_map = {
            10: [(0.7, 0.7), (0.9, 0.7), (0.9, 0.9), (0.7, 0.9)],
        }
        det = make_detection_result(
            polygon=[(0.1, 0.1), (0.3, 0.1), (0.3, 0.3), (0.1, 0.3)]
        )
        assert _match_roi(det, roi_map) is None

    def test_empty_map_returns_none(self):
        det = make_detection_result()
        assert _match_roi(det, {}) is None


class TestPersistDetections:
    def test_creates_events_with_matched_roi(self):
        mock_db = MagicMock()
        ctx = CameraDetectionContext(
            camera_id=1,
            rois=[RoiContext(roi_id=10, polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])],
            active_rules=[],
        )
        det = make_detection_result(
            label="bottle", confidence=0.85,
            polygon=[(0.1, 0.1), (0.3, 0.1), (0.3, 0.3), (0.1, 0.3)],
        )
        now = datetime.now(timezone.utc)

        DetectionPipeline._persist_detections(
            camera_id=1,
            detections=[det],
            detector_type=DetectorType.yolo,
            context=ctx,
            evidence_path="/evidence/1.jpg",
            captured_at=now,
            db=mock_db,
        )

        assert mock_db.add.call_count == 1
        event = mock_db.add.call_args[0][0]
        assert event.camera_id == 1
        assert event.roi_id == 10
        assert event.detector_type == DetectorType.yolo
        assert event.confidence == 0.85
        assert event.evidence_path == "/evidence/1.jpg"
        assert event.event_metadata["label"] == "bottle"
        assert event.event_metadata["polygon"] == [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]
        assert "area_ratio" in event.event_metadata
        mock_db.flush.assert_called_once()

    def test_no_flush_when_no_detections(self):
        mock_db = MagicMock()
        ctx = CameraDetectionContext(camera_id=1, rois=[], active_rules=[])

        DetectionPipeline._persist_detections(
            camera_id=1,
            detections=[],
            detector_type=DetectorType.yolo,
            context=ctx,
            evidence_path=None,
            captured_at=datetime.now(timezone.utc),
            db=mock_db,
        )

        mock_db.add.assert_not_called()
        mock_db.flush.assert_not_called()

    def test_multiple_detections(self):
        mock_db = MagicMock()
        ctx = CameraDetectionContext(
            camera_id=1,
            rois=[RoiContext(roi_id=10, polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])],
            active_rules=[],
        )
        d1 = make_detection_result(label="bottle", confidence=0.8)
        d2 = make_detection_result(label="trash", confidence=0.6)

        DetectionPipeline._persist_detections(
            camera_id=1,
            detections=[d1, d2],
            detector_type=DetectorType.yolo,
            context=ctx,
            evidence_path="/evidence.jpg",
            captured_at=datetime.now(timezone.utc),
            db=mock_db,
        )

        assert mock_db.add.call_count == 2

    def test_roi_id_none_when_no_match(self):
        mock_db = MagicMock()
        ctx = CameraDetectionContext(
            camera_id=1,
            rois=[RoiContext(roi_id=10, polygon=[(0.7, 0.7), (0.9, 0.7), (0.9, 0.9), (0.7, 0.9)])],
            active_rules=[],
        )
        det = make_detection_result(
            polygon=[(0.1, 0.1), (0.3, 0.1), (0.3, 0.3), (0.1, 0.3)]
        )

        DetectionPipeline._persist_detections(
            camera_id=1,
            detections=[det],
            detector_type=DetectorType.yolo,
            context=ctx,
            evidence_path=None,
            captured_at=datetime.now(timezone.utc),
            db=mock_db,
        )

        event = mock_db.add.call_args[0][0]
        assert event.roi_id is None
