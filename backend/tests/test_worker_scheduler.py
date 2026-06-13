"""Unit tests for workers.scheduler.InspectionScheduler."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from workers.executor import BatchExecutor
from workers.metrics import WorkerMetricsCollector
from workers.models import InspectionResult, ScheduledCamera, WorkerStatus
from workers.scheduler import BACKOFF_SECONDS, InspectionScheduler


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_scheduler(**overrides):
    settings = MagicMock()
    settings.alarm_interval_minutes = 5
    executor = MagicMock(spec=BatchExecutor)
    executor.execute_batch = AsyncMock(return_value=[])
    metrics = MagicMock(spec=WorkerMetricsCollector)
    metrics.record_inspection = AsyncMock()
    metrics.set_cameras_active = AsyncMock()
    defaults = dict(
        settings=settings,
        executor=executor,
        metrics=metrics,
        tick_seconds=0.01,
        sync_interval_seconds=9999.0,
    )
    defaults.update(overrides)
    return InspectionScheduler(**defaults)


def make_result(
    camera_id: int = 1,
    success: bool = True,
    duration_ms: float = 100.0,
    error: str | None = None,
) -> InspectionResult:
    return InspectionResult(
        camera_id=camera_id,
        success=success,
        image_bytes=b"img" if success else None,
        error=error,
        duration_ms=duration_ms,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# default_interval_seconds
# ---------------------------------------------------------------------------


class TestDefaultInterval:
    def test_reads_from_settings(self):
        scheduler = make_scheduler()
        assert scheduler.default_interval_seconds == 300.0  # 5 * 60

    def test_minimum_is_one(self):
        settings = MagicMock()
        settings.alarm_interval_minutes = 0
        scheduler = make_scheduler(settings=settings)
        assert scheduler.default_interval_seconds == 1.0


# ---------------------------------------------------------------------------
# add_camera
# ---------------------------------------------------------------------------


class TestAddCamera:
    def test_adds_to_schedule(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        assert 1 in scheduler._scheduled
        assert scheduler._scheduled[1].camera_id == 1

    def test_next_run_at_is_near_now(self):
        scheduler = make_scheduler()
        before = time.monotonic()
        scheduler.add_camera(1)
        after = time.monotonic()
        sc = scheduler._scheduled[1]
        assert before <= sc.next_run_at <= after + 0.1

    def test_uses_default_interval_when_none(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        assert scheduler._scheduled[1].interval_seconds == 300.0

    def test_uses_custom_interval(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1, interval_seconds=60.0)
        assert scheduler._scheduled[1].interval_seconds == 60.0

    def test_overwrites_existing(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler.add_camera(1, interval_seconds=120.0)
        assert len(scheduler._scheduled) == 1
        assert scheduler._scheduled[1].interval_seconds == 120.0


# ---------------------------------------------------------------------------
# remove_camera
# ---------------------------------------------------------------------------


class TestRemoveCamera:
    def test_removes_existing(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler.remove_camera(1)
        assert 1 not in scheduler._scheduled

    def test_noop_for_missing(self):
        scheduler = make_scheduler()
        scheduler.remove_camera(999)  # should not raise


# ---------------------------------------------------------------------------
# update_interval
# ---------------------------------------------------------------------------


class TestUpdateInterval:
    def test_updates_existing_camera(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1, interval_seconds=300.0)
        scheduler.update_interval(1, 60.0)
        assert scheduler._scheduled[1].interval_seconds == 60.0

    def test_adds_if_not_present(self):
        scheduler = make_scheduler()
        scheduler.update_interval(5, 120.0)
        assert 5 in scheduler._scheduled
        assert scheduler._scheduled[5].interval_seconds == 120.0

    def test_reschedules_next_run(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1, interval_seconds=300.0)
        old_next = scheduler._scheduled[1].next_run_at
        scheduler.update_interval(1, 60.0)
        # next_run_at should be at most now + 60
        assert scheduler._scheduled[1].next_run_at <= time.monotonic() + 60.0

    def test_minimum_one_second(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler.update_interval(1, 0.5)
        assert scheduler._scheduled[1].interval_seconds == 1.0


# ---------------------------------------------------------------------------
# _backoff_for
# ---------------------------------------------------------------------------


class TestBackoffFor:
    def test_first_failure(self):
        assert InspectionScheduler._backoff_for(1) == BACKOFF_SECONDS[0]

    def test_second_failure(self):
        assert InspectionScheduler._backoff_for(2) == BACKOFF_SECONDS[1]

    def test_third_failure(self):
        assert InspectionScheduler._backoff_for(3) == BACKOFF_SECONDS[2]

    def test_fourth_and_beyond_capped(self):
        expected = BACKOFF_SECONDS[-1]  # 300.0
        assert InspectionScheduler._backoff_for(4) == expected
        assert InspectionScheduler._backoff_for(10) == expected
        assert InspectionScheduler._backoff_for(100) == expected

    def test_all_backoff_values(self):
        for i, expected in enumerate(BACKOFF_SECONDS, start=1):
            assert InspectionScheduler._backoff_for(i) == expected


# ---------------------------------------------------------------------------
# _normalize_interval
# ---------------------------------------------------------------------------


class TestNormalizeInterval:
    def test_none_uses_default(self):
        scheduler = make_scheduler()
        assert scheduler._normalize_interval(None) == 300.0

    def test_valid_value_passes(self):
        scheduler = make_scheduler()
        assert scheduler._normalize_interval(60.0) == 60.0

    def test_minimum_one(self):
        scheduler = make_scheduler()
        assert scheduler._normalize_interval(0.1) == 1.0


# ---------------------------------------------------------------------------
# start / stop lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    @patch.object(InspectionScheduler, "_load_schedulable_camera_ids", return_value=[])
    def test_start_transitions_to_running(self, mock_load):
        scheduler = make_scheduler()

        async def _start_and_stop():
            task = asyncio.create_task(scheduler.start())
            await asyncio.sleep(0.05)
            assert scheduler.status == WorkerStatus.running
            await scheduler.stop()
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        run(_start_and_stop())

    @patch.object(InspectionScheduler, "_load_schedulable_camera_ids", return_value=[])
    def test_stop_sets_stopping_then_stopped(self, mock_load):
        scheduler = make_scheduler()

        async def _lifecycle():
            task = asyncio.create_task(scheduler.start())
            await asyncio.sleep(0.05)
            await scheduler.stop()
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            assert scheduler.status == WorkerStatus.stopped

        run(_lifecycle())

    def test_initial_status_is_idle(self):
        scheduler = make_scheduler()
        assert scheduler.status == WorkerStatus.idle


# ---------------------------------------------------------------------------
# _tick
# ---------------------------------------------------------------------------


class TestTick:
    def test_finds_due_cameras_and_runs_batch(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler.add_camera(2)
        # Make both due by setting next_run_at to past
        now = time.monotonic()
        scheduler._last_sync_at = now
        scheduler._scheduled[1].next_run_at = now - 1
        scheduler._scheduled[2].next_run_at = now - 1

        run(scheduler._tick())

        scheduler._executor.execute_batch.assert_called_once()
        called_ids = scheduler._executor.execute_batch.call_args[0][0]
        assert sorted(called_ids) == [1, 2]

    def test_skips_not_due_cameras(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        # Set next_run_at far in the future
        scheduler._scheduled[1].next_run_at = time.monotonic() + 9999

        run(scheduler._tick())
        scheduler._executor.execute_batch.assert_not_called()

    def test_skips_already_running_cameras(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler._scheduled[1].next_run_at = time.monotonic() - 1
        scheduler._scheduled[1].running = True

        run(scheduler._tick())
        scheduler._executor.execute_batch.assert_not_called()

    def test_nothing_scheduled_no_error(self):
        scheduler = make_scheduler()
        run(scheduler._tick())  # should not raise


# ---------------------------------------------------------------------------
# _run_due_batch — backoff on failure
# ---------------------------------------------------------------------------


class TestRunDueBatch:
    def test_success_resets_failures_and_reschedules(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler._scheduled[1].consecutive_failures = 3
        scheduler._scheduled[1].running = True

        result = make_result(camera_id=1, success=True)
        scheduler._executor.execute_batch = AsyncMock(return_value=[result])

        now = time.monotonic()
        run(scheduler._run_due_batch([1]))

        sc = scheduler._scheduled[1]
        assert sc.consecutive_failures == 0
        assert sc.running is False
        assert sc.next_run_at > now

    def test_failure_increments_failures_and_applies_backoff(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler._scheduled[1].running = True

        result = make_result(camera_id=1, success=False, error="fail")
        scheduler._executor.execute_batch = AsyncMock(return_value=[result])

        now = time.monotonic()
        run(scheduler._run_due_batch([1]))

        sc = scheduler._scheduled[1]
        assert sc.consecutive_failures == 1
        assert sc.running is False
        assert sc.next_run_at >= now + BACKOFF_SECONDS[0] - 0.1

    def test_cumulative_failures_apply_escalating_backoff(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)

        for failure_count in range(1, 5):
            scheduler._scheduled[1].running = True
            result = make_result(camera_id=1, success=False, error="fail")
            scheduler._executor.execute_batch = AsyncMock(return_value=[result])
            run(scheduler._run_due_batch([1]))

            expected_backoff = BACKOFF_SECONDS[min(failure_count, len(BACKOFF_SECONDS)) - 1]
            assert scheduler._scheduled[1].consecutive_failures == failure_count

    def test_unknown_camera_result_ignored(self):
        scheduler = make_scheduler()
        scheduler.add_camera(1)

        result = make_result(camera_id=99, success=True)
        scheduler._executor.execute_batch = AsyncMock(return_value=[result])
        run(scheduler._run_due_batch([99]))

        # Camera 1 should remain untouched
        assert 99 not in scheduler._scheduled


# ---------------------------------------------------------------------------
# sync_cameras_from_db
# ---------------------------------------------------------------------------


class TestSyncCamerasFromDb:
    @patch.object(InspectionScheduler, "_load_schedulable_camera_ids", return_value=[1, 2, 3])
    def test_adds_new_cameras_from_db(self, mock_load):
        scheduler = make_scheduler()
        run(scheduler.sync_cameras_from_db())

        assert 1 in scheduler._scheduled
        assert 2 in scheduler._scheduled
        assert 3 in scheduler._scheduled
        assert len(scheduler._scheduled) == 3

    @patch.object(InspectionScheduler, "_load_schedulable_camera_ids", return_value=[1])
    def test_removes_cameras_not_in_db(self, mock_load):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler.add_camera(2)

        run(scheduler.sync_cameras_from_db())

        assert 1 in scheduler._scheduled
        assert 2 not in scheduler._scheduled

    @patch.object(InspectionScheduler, "_load_schedulable_camera_ids", return_value=[])
    def test_empty_db_removes_all(self, mock_load):
        scheduler = make_scheduler()
        scheduler.add_camera(1)
        scheduler.add_camera(2)

        run(scheduler.sync_cameras_from_db())
        assert len(scheduler._scheduled) == 0

    @patch.object(InspectionScheduler, "_load_schedulable_camera_ids", return_value=[1, 2])
    def test_sets_cameras_active_count(self, mock_load):
        scheduler = make_scheduler()
        run(scheduler.sync_cameras_from_db())

        scheduler.metrics.set_cameras_active.assert_called_with(2)
