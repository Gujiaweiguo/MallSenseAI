"""Snapshot capture service with in-memory caching."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.app.camera.adapter import CameraCaptureError, CameraHealth, HealthStatus
from backend.app.camera.registry import CameraRegistry

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from backend.app.models.entities import Camera, CameraStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------


@dataclass
class _CacheEntry:
    image_bytes: bytes
    captured_at: float  # unix timestamp
    camera_health: CameraHealth


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class CaptureResult:
    """Result of a capture attempt."""

    image_bytes: bytes
    captured_at: float  # unix timestamp
    from_cache: bool
    camera_health: CameraHealth


# ---------------------------------------------------------------------------
# Capture service
# ---------------------------------------------------------------------------


class CaptureService:
    """Manages snapshot capture with an in-memory TTL cache.

    Parameters
    ----------
    cache_ttl:
        Time-to-live for cached snapshots in seconds (default 30).
    timeout:
        HTTP timeout for the underlying adapter in seconds (default 10).
    """

    def __init__(
        self,
        *,
        cache_ttl: float = 30.0,
        timeout: float = 10.0,
        registry: CameraRegistry | None = None,
    ) -> None:
        self._cache_ttl = cache_ttl
        self._timeout = timeout
        self._registry = registry or CameraRegistry.get_instance()
        self._cache: dict[int, _CacheEntry] = {}

    # -- public API ---------------------------------------------------------

    async def capture(self, camera_id: int, db: Session) -> CaptureResult:
        """Capture a snapshot for the given camera.

        Returns from cache when the entry is still fresh.  On capture
        failure the camera status in the DB is updated to *degraded* or
        *error*.
        """
        camera = self._get_camera_record(camera_id, db)
        now = time.time()

        # 1. Try cache hit
        cached = self._cache.get(camera_id)
        if cached is not None and (now - cached.captured_at) < self._cache_ttl:
            return CaptureResult(
                image_bytes=cached.image_bytes,
                captured_at=cached.captured_at,
                from_cache=True,
                camera_health=cached.camera_health,
            )

        # 2. Perform real capture
        camera._plain_password = camera.password_hash
        adapter = self._registry.get_adapter(camera, timeout=self._timeout)
        # Attach plain password so the adapter can authenticate.
        # The service layer is responsible for decryption before calling us.
        try:
            image_bytes = await adapter.capture_snapshot()
            health = adapter.get_health()
            self._update_camera_status(db, camera, "active", health)
            self._cache[camera_id] = _CacheEntry(
                image_bytes=image_bytes,
                captured_at=time.time(),
                camera_health=health,
            )
            return CaptureResult(
                image_bytes=image_bytes,
                captured_at=time.time(),
                from_cache=False,
                camera_health=health,
            )
        except CameraCaptureError as exc:
            logger.warning("Capture failed for camera %d: %s", camera_id, exc)
            health = adapter.get_health()
            self._update_camera_status(db, camera, _health_to_db_status(health), health)
            raise

    def invalidate_cache(self, camera_id: int | None = None) -> None:
        """Remove cached snapshot(s).  ``None`` clears the entire cache."""
        if camera_id is None:
            self._cache.clear()
        else:
            self._cache.pop(camera_id, None)

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _get_camera_record(camera_id: int, db: Session) -> Camera:
        from backend.app.models.entities import Camera

        camera = db.get(Camera, camera_id)
        if camera is None:
            raise ValueError(f"Camera id={camera_id} not found")
        return camera

    @staticmethod
    def _update_camera_status(
        db: Session,
        camera: Camera,
        status: str,
        health: CameraHealth,
    ) -> None:
        """Persist camera status and metadata to DB."""
        from backend.app.models.entities import CameraStatus as CS

        new_status = CS(status) if isinstance(status, str) else status
        if camera.status != new_status:
            camera.status = new_status
            db.commit()
            logger.info("Camera %d status -> %s", camera.id, new_status.value)


def _health_to_db_status(health: CameraHealth) -> str:
    """Map runtime health to a DB ``CameraStatus`` value."""
    if health.status == HealthStatus.online:
        return "active"
    if health.status == HealthStatus.degraded:
        return "maintenance"
    return "error"
