"""Camera health-check service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.app.camera.adapter import CameraHealth
from backend.app.camera.registry import CameraRegistry

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Periodic / on-demand health checker for cameras."""

    def __init__(self, registry: CameraRegistry | None = None) -> None:
        self._registry = registry or CameraRegistry.get_instance()

    async def check_camera(self, camera_id: int, db: Session) -> CameraHealth:
        """Check a single camera and persist the resulting status."""
        from backend.app.models.entities import Camera, CameraStatus

        camera = db.get(Camera, camera_id)
        if camera is None:
            raise ValueError(f"Camera id={camera_id} not found")

        adapter = self._registry.get_adapter(camera)
        health = await adapter.check_health()

        # Map health status to DB enum.
        status_map = {
            "online": CameraStatus.active,
            "degraded": CameraStatus.maintenance,
            "offline": CameraStatus.error,
        }
        new_status = status_map.get(health.status.value, CameraStatus.error)

        if camera.status != new_status:
            camera.status = new_status
            db.commit()
            logger.info(
                "Health check: camera %d -> %s (failures=%d)",
                camera_id,
                new_status.value,
                health.consecutive_failures,
            )

        return health

    async def check_all_cameras(self, db: Session) -> dict[int, CameraHealth]:
        """Check every camera in the DB and return per-camera health."""
        import asyncio

        from backend.app.models.entities import Camera

        cameras: list[Camera] = db.query(Camera).all()
        results: dict[int, CameraHealth] = {}

        async def _check(cam: Camera) -> tuple[int, CameraHealth]:
            try:
                h = await self.check_camera(cam.id, db)
                return cam.id, h
            except Exception:
                return cam.id, CameraHealth()

        for coro in asyncio.as_completed([_check(c) for c in cameras]):
            cam_id, health = await coro
            results[cam_id] = health

        return results
