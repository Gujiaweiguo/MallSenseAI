"""Concurrent camera inspection execution."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from backend.app.camera.capture import CaptureService
from backend.app.camera.health import HealthCheckService
from backend.app.db.session import SessionLocal

from workers.models import InspectionResult

logger = logging.getLogger(__name__)


class InspectionExecutor:
    """Executes one camera inspection by capturing a snapshot."""

    def __init__(
        self,
        *,
        capture_service: CaptureService | None = None,
        health_service: HealthCheckService | None = None,
    ) -> None:
        self._capture_service: CaptureService = capture_service or CaptureService()
        self._health_service: HealthCheckService = health_service or HealthCheckService()

    async def execute(self, camera_id: int) -> InspectionResult:
        """Capture a snapshot for one camera and isolate all failures."""
        start = time.monotonic()
        timestamp = datetime.now(timezone.utc)
        image_bytes: bytes | None = None
        error: str | None = None

        db = SessionLocal()
        try:
            capture = await self._capture_service.capture(camera_id, db)
            image_bytes = capture.image_bytes
            success = True
        except Exception as exc:  # noqa: BLE001 - worker must isolate camera failures
            success = False
            error = str(exc)
            logger.warning("Inspection failed for camera %d: %s", camera_id, exc)
            try:
                _ = await self._health_service.check_camera(camera_id, db)
            except Exception as health_exc:  # noqa: BLE001
                logger.debug(
                    "Health check after inspection failure also failed for camera %d: %s",
                    camera_id,
                    health_exc,
                )
        finally:
            db.close()

        duration_ms = (time.monotonic() - start) * 1000
        return InspectionResult(
            camera_id=camera_id,
            success=success,
            image_bytes=image_bytes,
            error=error,
            duration_ms=duration_ms,
            timestamp=timestamp,
        )


class BatchExecutor:
    """Executes camera inspections concurrently with bounded fan-out."""

    def __init__(self, executor: InspectionExecutor | None = None) -> None:
        self._executor: InspectionExecutor = executor or InspectionExecutor()

    async def execute_batch(
        self,
        camera_ids: list[int],
        max_concurrency: int = 10,
    ) -> list[InspectionResult]:
        """Inspect cameras concurrently; one failure never cancels siblings."""
        if not camera_ids:
            return []

        semaphore = asyncio.Semaphore(max(1, max_concurrency))

        async def _execute_one(camera_id: int) -> InspectionResult:
            async with semaphore:
                try:
                    return await self._executor.execute(camera_id)
                except Exception as exc:  # noqa: BLE001 - final isolation guard
                    logger.exception("Unhandled inspection error for camera %d", camera_id)
                    return InspectionResult(
                        camera_id=camera_id,
                        success=False,
                        image_bytes=None,
                        error=str(exc),
                        duration_ms=0.0,
                        timestamp=datetime.now(timezone.utc),
                    )

        return await asyncio.gather(*(_execute_one(camera_id) for camera_id in camera_ids))
