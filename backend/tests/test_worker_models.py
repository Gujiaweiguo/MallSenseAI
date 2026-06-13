"""Unit tests for workers.models dataclasses and enums."""

from __future__ import annotations

from datetime import datetime, timezone

from workers.models import (
    CameraInspectionMetrics,
    InspectionResult,
    ScheduledCamera,
    WorkerMetrics,
    WorkerStatus,
)


# ---------------------------------------------------------------------------
# WorkerStatus enum
# ---------------------------------------------------------------------------


class TestWorkerStatus:
    def test_all_values(self):
        expected = {"idle", "running", "stopping", "stopped", "error"}
        actual = {s.value for s in WorkerStatus}
        assert actual == expected

    def test_member_count(self):
        assert len(WorkerStatus) == 5

    def test_is_string_enum(self):
        assert isinstance(WorkerStatus.idle, str)
        assert WorkerStatus.idle == "idle"

    def test_comparison(self):
        assert WorkerStatus.running == WorkerStatus.running
        assert WorkerStatus.idle != WorkerStatus.running


# ---------------------------------------------------------------------------
# InspectionResult
# ---------------------------------------------------------------------------


class TestInspectionResult:
    def test_construction_all_fields(self):
        ts = datetime.now(timezone.utc)
        r = InspectionResult(
            camera_id=1,
            success=True,
            image_bytes=b"img",
            error=None,
            duration_ms=42.5,
            timestamp=ts,
        )
        assert r.camera_id == 1
        assert r.success is True
        assert r.image_bytes == b"img"
        assert r.error is None
        assert r.duration_ms == 42.5
        assert r.timestamp is ts

    def test_failure_result(self):
        r = InspectionResult(
            camera_id=2,
            success=False,
            image_bytes=None,
            error="timeout",
            duration_ms=100.0,
            timestamp=datetime.now(timezone.utc),
        )
        assert r.success is False
        assert r.image_bytes is None
        assert r.error == "timeout"

    def test_has_slots(self):
        r = InspectionResult(
            camera_id=1,
            success=True,
            image_bytes=b"",
            error=None,
            duration_ms=0.0,
            timestamp=datetime.now(timezone.utc),
        )
        assert hasattr(type(r), "__slots__")

    def test_field_count(self):
        expected_fields = {
            "camera_id", "success", "image_bytes",
            "error", "duration_ms", "timestamp",
        }
        assert set(InspectionResult.__dataclass_fields__.keys()) == expected_fields


# ---------------------------------------------------------------------------
# WorkerMetrics
# ---------------------------------------------------------------------------


class TestWorkerMetrics:
    def test_defaults(self):
        m = WorkerMetrics()
        assert m.total_inspections == 0
        assert m.successful == 0
        assert m.failed == 0
        assert m.avg_duration_ms == 0.0
        assert m.last_run_at is None
        assert m.cameras_active == 0

    def test_custom_values(self):
        ts = datetime.now(timezone.utc)
        m = WorkerMetrics(
            total_inspections=10,
            successful=8,
            failed=2,
            avg_duration_ms=55.0,
            last_run_at=ts,
            cameras_active=3,
        )
        assert m.total_inspections == 10
        assert m.successful == 8
        assert m.failed == 2
        assert m.avg_duration_ms == 55.0
        assert m.last_run_at is ts
        assert m.cameras_active == 3

    def test_has_slots(self):
        assert hasattr(type(WorkerMetrics()), "__slots__")


# ---------------------------------------------------------------------------
# CameraInspectionMetrics
# ---------------------------------------------------------------------------


class TestCameraInspectionMetrics:
    def test_defaults(self):
        m = CameraInspectionMetrics(camera_id=5)
        assert m.camera_id == 5
        assert m.total == 0
        assert m.successful == 0
        assert m.failed == 0
        assert m.avg_duration_ms == 0.0
        assert m.last_success_at is None
        assert m.last_failure_at is None
        assert m.consecutive_failures == 0

    def test_custom_values(self):
        ts = datetime.now(timezone.utc)
        m = CameraInspectionMetrics(
            camera_id=3,
            total=20,
            successful=18,
            failed=2,
            avg_duration_ms=120.0,
            last_success_at=ts,
            last_failure_at=None,
            consecutive_failures=0,
        )
        assert m.total == 20
        assert m.successful == 18
        assert m.failed == 2
        assert m.avg_duration_ms == 120.0
        assert m.last_success_at is ts

    def test_has_slots(self):
        assert hasattr(type(CameraInspectionMetrics(camera_id=1)), "__slots__")


# ---------------------------------------------------------------------------
# ScheduledCamera
# ---------------------------------------------------------------------------


class TestScheduledCamera:
    def test_construction(self):
        sc = ScheduledCamera(
            camera_id=7,
            interval_seconds=300.0,
            next_run_at=100.0,
        )
        assert sc.camera_id == 7
        assert sc.interval_seconds == 300.0
        assert sc.next_run_at == 100.0
        assert sc.consecutive_failures == 0
        assert sc.running is False

    def test_custom_values(self):
        sc = ScheduledCamera(
            camera_id=1,
            interval_seconds=60.0,
            next_run_at=50.0,
            consecutive_failures=3,
            running=True,
        )
        assert sc.consecutive_failures == 3
        assert sc.running is True

    def test_has_slots(self):
        assert hasattr(type(ScheduledCamera(camera_id=1, interval_seconds=1.0, next_run_at=0.0)), "__slots__")
