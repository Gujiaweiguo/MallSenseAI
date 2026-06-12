"""Inspection worker entry point."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from backend.app.db.session import SessionLocal
from backend.app.detectors import DebrisDetector, DetectorRegistry, FireSmokeDetector
from backend.app.notifications.router import start_notification_router, stop_notification_router
from backend.app.notifications.service import NotificationService
from backend.app.rules.cooldown import CooldownTracker
from workers.pipeline import DetectionPipeline
from workers.scheduler import InspectionScheduler

logger = logging.getLogger(__name__)


def _build_detector_registry() -> DetectorRegistry:
    registry = DetectorRegistry()

    try:
        detector = DebrisDetector()
        if detector.is_enabled:
            registry.register("debris", detector)
        else:
            logger.warning("Debris detector disabled — model not available")
    except Exception:
        logger.warning("Failed to initialize DebrisDetector", exc_info=True)

    try:
        detector = FireSmokeDetector()
        if detector.is_enabled:
            registry.register("fire_smoke", detector)
        else:
            logger.warning("Fire/smoke detector disabled — model not available")
    except Exception:
        logger.warning("Failed to initialize FireSmokeDetector", exc_info=True)

    logger.info("Detector registry: %s", registry)
    return registry


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    # Detectors (graceful degradation if model weights missing)
    registry = _build_detector_registry()

    # Notification router (optional — works without notification groups)
    notification_service: NotificationService | None = None
    try:
        notification_service = NotificationService(SessionLocal)
        start_notification_router(notification_service)
        logger.info("Notification router started")
    except Exception:
        logger.warning("Notification service unavailable", exc_info=True)

    # Pipeline
    pipeline = DetectionPipeline(
        detector_registry=registry,
        cooldown_tracker=CooldownTracker(),
    )

    scheduler = InspectionScheduler(pipeline=pipeline)
    loop = asyncio.get_running_loop()

    stop_requested = asyncio.Event()

    def _request_stop() -> None:
        logger.info("Shutdown signal received")
        stop_requested.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _request_stop)

    scheduler_task = asyncio.create_task(scheduler.start(), name="inspection-scheduler")
    _ = await stop_requested.wait()
    await scheduler.stop()
    _ = await scheduler_task

    # Cleanup
    stop_notification_router()
    logger.info("Worker shutdown complete")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
