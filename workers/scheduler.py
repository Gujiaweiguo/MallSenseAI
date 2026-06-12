"""Async inspection scheduler for periodic camera captures."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress

from sqlalchemy import select

from backend.app.core.config import Settings, get_settings
from backend.app.db.session import SessionLocal
from backend.app.models.entities import Camera, CameraStatus

from workers.executor import BatchExecutor
from workers.metrics import WorkerMetricsCollector
from workers.models import ScheduledCamera, WorkerStatus

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = (30.0, 60.0, 120.0, 300.0)


class InspectionScheduler:
    """Schedules periodic inspections with failure backoff and isolation."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        executor: BatchExecutor | None = None,
        metrics: WorkerMetricsCollector | None = None,
        max_concurrency: int = 10,
        sync_interval_seconds: float = 60.0,
        tick_seconds: float = 1.0,
    ) -> None:
        self._settings: Settings = settings or get_settings()
        self._executor: BatchExecutor = executor or BatchExecutor()
        self.metrics: WorkerMetricsCollector = metrics or WorkerMetricsCollector()
        self._max_concurrency: int = max_concurrency
        self._sync_interval_seconds: float = sync_interval_seconds
        self._tick_seconds: float = tick_seconds
        self._scheduled: dict[int, ScheduledCamera] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._stop_event: asyncio.Event = asyncio.Event()
        self.status: WorkerStatus = WorkerStatus.idle
        self._last_sync_at: float = 0.0

    @property
    def default_interval_seconds(self) -> float:
        """Default camera inspection interval derived from settings."""
        return max(1.0, float(self._settings.alarm_interval_minutes * 60))

    def add_camera(self, camera_id: int, interval_seconds: float | None = None) -> None:
        """Schedule a camera for periodic inspection."""
        interval = self._normalize_interval(interval_seconds)
        self._scheduled[camera_id] = ScheduledCamera(
            camera_id=camera_id,
            interval_seconds=interval,
            next_run_at=time.monotonic(),
        )
        logger.info("Scheduled camera %d every %.0fs", camera_id, interval)

    def remove_camera(self, camera_id: int) -> None:
        """Remove a camera from the schedule."""
        if self._scheduled.pop(camera_id, None) is not None:
            logger.info("Unscheduled camera %d", camera_id)

    def update_interval(self, camera_id: int, interval_seconds: float) -> None:
        """Change the inspection frequency for a scheduled camera."""
        interval = self._normalize_interval(interval_seconds)
        scheduled = self._scheduled.get(camera_id)
        if scheduled is None:
            self.add_camera(camera_id, interval)
            return
        scheduled.interval_seconds = interval
        scheduled.next_run_at = min(scheduled.next_run_at, time.monotonic() + interval)
        logger.info("Updated camera %d interval to %.0fs", camera_id, interval)

    async def start(self) -> None:
        """Run the scheduling loop until stopped."""
        if self.status == WorkerStatus.running:
            return

        self.status = WorkerStatus.running
        self._stop_event.clear()
        logger.info("Inspection scheduler starting")
        try:
            await self.sync_cameras_from_db()
            while not self._stop_event.is_set():
                await self._tick()
                with suppress(asyncio.TimeoutError):
                    _ = await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._tick_seconds,
                    )
        except asyncio.CancelledError:
            self.status = WorkerStatus.stopping
            raise
        except Exception:
            self.status = WorkerStatus.error
            logger.exception("Inspection scheduler stopped after an unexpected error")
            raise
        finally:
            await self._drain_running_tasks()
            if self.status != WorkerStatus.error:
                self.status = WorkerStatus.stopped
            logger.info("Inspection scheduler stopped")

    async def stop(self) -> None:
        """Request graceful shutdown and wait for active inspections."""
        if self.status == WorkerStatus.running:
            self.status = WorkerStatus.stopping
        self._stop_event.set()
        await self._drain_running_tasks()

    async def sync_cameras_from_db(self) -> None:
        """Synchronize in-memory schedule with active/degraded DB cameras."""
        camera_ids = await asyncio.to_thread(self._load_schedulable_camera_ids)
        configured = set(self._scheduled)
        db_ids = set(camera_ids)

        for camera_id in sorted(db_ids - configured):
            self.add_camera(camera_id, self.default_interval_seconds)
        for camera_id in sorted(configured - db_ids):
            self.remove_camera(camera_id)

        await self.metrics.set_cameras_active(len(self._scheduled))
        self._last_sync_at = time.monotonic()

    async def _tick(self) -> None:
        now = time.monotonic()
        if now - self._last_sync_at >= self._sync_interval_seconds:
            await self.sync_cameras_from_db()

        due = [
            camera.camera_id
            for camera in self._scheduled.values()
            if camera.next_run_at <= now and not camera.running
        ]
        if not due:
            return

        for camera_id in due:
            self._scheduled[camera_id].running = True

        task = asyncio.create_task(self._run_due_batch(due), name="inspection-batch")
        self._tasks.add(task)
        _ = task.add_done_callback(self._tasks.discard)

    async def _run_due_batch(self, camera_ids: list[int]) -> None:
        results = await self._executor.execute_batch(camera_ids, self._max_concurrency)
        now = time.monotonic()
        for result in results:
            await self.metrics.record_inspection(result)
            scheduled = self._scheduled.get(result.camera_id)
            if scheduled is None:
                continue

            scheduled.running = False
            if result.success:
                scheduled.consecutive_failures = 0
                scheduled.next_run_at = now + scheduled.interval_seconds
            else:
                scheduled.consecutive_failures += 1
                scheduled.next_run_at = now + self._backoff_for(scheduled.consecutive_failures)

    async def _drain_running_tasks(self) -> None:
        if not self._tasks:
            return
        _ = await asyncio.gather(*self._tasks, return_exceptions=True)

    def _normalize_interval(self, interval_seconds: float | None) -> float:
        if interval_seconds is None:
            return self.default_interval_seconds
        return max(1.0, float(interval_seconds))

    @staticmethod
    def _backoff_for(consecutive_failures: int) -> float:
        index = min(max(consecutive_failures, 1), len(BACKOFF_SECONDS)) - 1
        return BACKOFF_SECONDS[index]

    @staticmethod
    def _load_schedulable_camera_ids() -> list[int]:
        db = SessionLocal()
        try:
            stmt = (
                select(Camera.id)
                .where(Camera.status.in_([CameraStatus.active, CameraStatus.maintenance]))
                .order_by(Camera.id)
            )
            return list(db.scalars(stmt).all())
        finally:
            db.close()
