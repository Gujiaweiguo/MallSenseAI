"""Camera adapter registry — maps DB camera records to adapter instances."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from backend.app.camera.adapter import CameraAdapter, DahuaCameraAdapter

if TYPE_CHECKING:
    from backend.app.models.entities import Camera

logger = logging.getLogger(__name__)


class CameraRegistry:
    """Creates and caches the correct adapter for a given camera record.

    Currently only Dahua cameras are supported.  To add a new vendor,
    extend ``_create_adapter`` and optionally inspect ``camera`` fields
    to pick the right class.
    """

    _instance: CameraRegistry | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._adapters: dict[int, CameraAdapter] = {}

    # -- singleton access ---------------------------------------------------

    @classmethod
    def get_instance(cls) -> CameraRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- public API ---------------------------------------------------------

    def get_adapter(self, camera: Camera, *, timeout: float = 10.0) -> CameraAdapter:
        """Return a cached adapter for *camera*, creating one if needed."""
        cam_id: int = camera.id  # type: ignore[assignment]
        existing = self._adapters.get(cam_id)
        if existing is not None:
            # Refresh connection details if they changed.
            info = existing.get_camera_info()
            if (
                info.ip != camera.ip
                or info.port != camera.port
                or info.username != camera.username
            ):
                del self._adapters[cam_id]
            else:
                return existing

        adapter = self._create_adapter(camera, timeout=timeout)
        self._adapters[cam_id] = adapter
        return adapter

    def invalidate(self, camera_id: int) -> None:
        """Remove cached adapter so next call rebuilds it."""
        self._adapters.pop(camera_id, None)

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _create_adapter(camera: Camera, *, timeout: float = 10.0) -> CameraAdapter:
        """Factory method.  Extend this when new camera vendors are added."""
        # Currently every camera is Dahua.
        password = getattr(camera, "_plain_password", "")  # set by service layer
        return DahuaCameraAdapter(
            ip=camera.ip,
            port=camera.port,
            username=camera.username,
            password=password,
            location=camera.location,
            timeout=timeout,
        )
