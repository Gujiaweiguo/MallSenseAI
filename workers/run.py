"""Inspection worker entry point."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from workers.scheduler import InspectionScheduler

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the scheduler and run until interrupted."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    scheduler = InspectionScheduler()
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


def run() -> None:
    """Synchronous console entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
