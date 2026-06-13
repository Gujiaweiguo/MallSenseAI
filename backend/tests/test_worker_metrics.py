"""Unit tests for workers.metrics.WorkerMetricsCollector and _rolling_average."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from workers.metrics import WorkerMetricsCollector, _rolling_average
from workers.models import CameraInspectionMetrics, InspectionResult, WorkerMetrics


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_result(
    camera_id: int = 1,
    success: bool = True,
    image_bytes: bytes = b"img",
    error: str | None = None,
    duration_ms: float = 100.0,
) -> InspectionResult:
    return InspectionResult(
        camera_id=camera_id,
        success=success,
        image_bytes=image_bytes,
        error=error,
        duration_ms=duration_ms,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# _rolling_average
# ---------------------------------------------------------------------------


class TestRollingAverage:
    def test_first_value(self):
        assert _rolling_average(0.0, 1, 50.0) == 50.0

    def test_first_value_from_nonzero(self):
        """Even if current_average is non-zero, count=1 means use new_value."""
        assert _rolling_average(999.0, 1, 42.0) == 42.0

    def test_second_value(self):
        avg = _rolling_average(100.0, 2, 200.0)
        assert avg == 100.0 + (200.0 - 100.0) / 2  # 150.0

    def test_third_value(self):
        avg = _rolling_average(150.0, 3, 300.0)
        assert avg == 150.0 + (300.0 - 150.0) / 3  # 200.0

    def test_decreasing_values(self):
        avg = _rolling_average(200.0, 2, 100.0)
        assert avg == 200.0 + (100.0 - 200.0) / 2  # 150.0


# ---------------------------------------------------------------------------
# record_inspection — aggregate metrics
# ---------------------------------------------------------------------------


class TestRecordInspectionAggregate:
    def test_single_success(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(success=True)))

        m = run(collector.get_metrics())
        assert m.total_inspections == 1
        assert m.successful == 1
        assert m.failed == 0
        assert m.avg_duration_ms == 100.0

    def test_single_failure(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(success=False, error="boom")))

        m = run(collector.get_metrics())
        assert m.total_inspections == 1
        assert m.successful == 0
        assert m.failed == 1

    def test_multiple_records(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(duration_ms=100.0)))
        run(collector.record_inspection(make_result(duration_ms=200.0)))

        m = run(collector.get_metrics())
        assert m.total_inspections == 2
        assert m.successful == 2
        assert m.avg_duration_ms == 150.0

    def test_mixed_success_failure(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(success=True)))
        run(collector.record_inspection(make_result(success=False, error="err")))
        run(collector.record_inspection(make_result(success=True)))

        m = run(collector.get_metrics())
        assert m.total_inspections == 3
        assert m.successful == 2
        assert m.failed == 1

    def test_last_run_at_updated(self):
        collector = WorkerMetricsCollector()
        ts1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2025, 6, 1, tzinfo=timezone.utc)

        r1 = InspectionResult(1, True, b"", None, 50.0, ts1)
        r2 = InspectionResult(1, True, b"", None, 50.0, ts2)
        run(collector.record_inspection(r1))
        run(collector.record_inspection(r2))

        m = run(collector.get_metrics())
        assert m.last_run_at is ts2


# ---------------------------------------------------------------------------
# record_inspection — per-camera metrics
# ---------------------------------------------------------------------------


class TestRecordInspectionPerCamera:
    def test_creates_camera_entry(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(camera_id=5)))

        cm = run(collector.get_camera_metrics(5))
        assert cm.camera_id == 5
        assert cm.total == 1
        assert cm.successful == 1

    def test_consecutive_failures_reset_on_success(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(camera_id=1, success=False, error="e")))
        run(collector.record_inspection(make_result(camera_id=1, success=False, error="e")))

        cm = run(collector.get_camera_metrics(1))
        assert cm.consecutive_failures == 2

        run(collector.record_inspection(make_result(camera_id=1, success=True)))
        cm = run(collector.get_camera_metrics(1))
        assert cm.consecutive_failures == 0

    def test_last_success_at_and_failure_at(self):
        collector = WorkerMetricsCollector()
        ts_success = datetime(2025, 3, 1, tzinfo=timezone.utc)
        ts_fail = datetime(2025, 3, 2, tzinfo=timezone.utc)

        r_ok = InspectionResult(1, True, b"", None, 50.0, ts_success)
        r_fail = InspectionResult(1, False, None, "err", 50.0, ts_fail)
        run(collector.record_inspection(r_ok))
        run(collector.record_inspection(r_fail))

        cm = run(collector.get_camera_metrics(1))
        assert cm.last_success_at is ts_success
        assert cm.last_failure_at is ts_fail

    def test_separate_cameras_isolated(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(camera_id=1, duration_ms=100.0)))
        run(collector.record_inspection(make_result(camera_id=2, duration_ms=200.0)))

        cm1 = run(collector.get_camera_metrics(1))
        cm2 = run(collector.get_camera_metrics(2))
        assert cm1.total == 1
        assert cm2.total == 1
        assert cm1.avg_duration_ms == 100.0
        assert cm2.avg_duration_ms == 200.0


# ---------------------------------------------------------------------------
# get_metrics returns copies
# ---------------------------------------------------------------------------


class TestGetMetricsCopy:
    def test_returns_copy(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result()))

        m = run(collector.get_metrics())
        m.total_inspections = 999

        m2 = run(collector.get_metrics())
        assert m2.total_inspections == 1  # original unchanged


class TestGetCameraMetricsCopy:
    def test_unknown_camera_returns_fresh(self):
        collector = WorkerMetricsCollector()
        cm = run(collector.get_camera_metrics(999))
        assert cm.camera_id == 999
        assert cm.total == 0

    def test_returns_copy(self):
        collector = WorkerMetricsCollector()
        run(collector.record_inspection(make_result(camera_id=1)))

        cm = run(collector.get_camera_metrics(1))
        cm.total = 999

        cm2 = run(collector.get_camera_metrics(1))
        assert cm2.total == 1


# ---------------------------------------------------------------------------
# set_cameras_active
# ---------------------------------------------------------------------------


class TestSetCamerasActive:
    def test_updates_count(self):
        collector = WorkerMetricsCollector()
        run(collector.set_cameras_active(5))
        m = run(collector.get_metrics())
        assert m.cameras_active == 5

    def test_overwrites_previous(self):
        collector = WorkerMetricsCollector()
        run(collector.set_cameras_active(5))
        run(collector.set_cameras_active(3))
        m = run(collector.get_metrics())
        assert m.cameras_active == 3
