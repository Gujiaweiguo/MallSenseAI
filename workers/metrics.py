"""Thread-safe worker metrics collection."""

from __future__ import annotations

import asyncio
from dataclasses import replace

from workers.models import CameraInspectionMetrics, InspectionResult, WorkerMetrics


class WorkerMetricsCollector:
    """Collects aggregate and per-camera inspection metrics."""

    def __init__(self) -> None:
        self._lock: asyncio.Lock = asyncio.Lock()
        self._metrics: WorkerMetrics = WorkerMetrics()
        self._camera_metrics: dict[int, CameraInspectionMetrics] = {}

    async def record_inspection(self, result: InspectionResult) -> None:
        """Record a single inspection result."""
        async with self._lock:
            self._metrics.total_inspections += 1
            self._metrics.last_run_at = result.timestamp
            if result.success:
                self._metrics.successful += 1
            else:
                self._metrics.failed += 1
            self._metrics.avg_duration_ms = _rolling_average(
                self._metrics.avg_duration_ms,
                self._metrics.total_inspections,
                result.duration_ms,
            )

            camera = self._camera_metrics.setdefault(
                result.camera_id,
                CameraInspectionMetrics(camera_id=result.camera_id),
            )
            camera.total += 1
            camera.avg_duration_ms = _rolling_average(
                camera.avg_duration_ms,
                camera.total,
                result.duration_ms,
            )
            if result.success:
                camera.successful += 1
                camera.last_success_at = result.timestamp
                camera.consecutive_failures = 0
            else:
                camera.failed += 1
                camera.last_failure_at = result.timestamp
                camera.consecutive_failures += 1

    async def get_metrics(self) -> WorkerMetrics:
        """Return a snapshot of aggregate worker metrics."""
        async with self._lock:
            return replace(self._metrics)

    async def get_camera_metrics(self, camera_id: int) -> CameraInspectionMetrics:
        """Return a snapshot of metrics for one camera."""
        async with self._lock:
            metrics = self._camera_metrics.get(camera_id)
            if metrics is None:
                return CameraInspectionMetrics(camera_id=camera_id)
            return replace(metrics)

    async def set_cameras_active(self, count: int) -> None:
        """Update the active scheduled camera count."""
        async with self._lock:
            self._metrics.cameras_active = count


def _rolling_average(current_average: float, new_count: int, new_value: float) -> float:
    if new_count <= 1:
        return new_value
    return current_average + ((new_value - current_average) / new_count)
