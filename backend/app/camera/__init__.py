"""Camera adapter, capture service, and health management."""

from __future__ import annotations

from backend.app.camera.adapter import CameraAdapter, CameraHealth, CameraInfo, DahuaCameraAdapter
from backend.app.camera.capture import CaptureResult, CaptureService
from backend.app.camera.health import HealthCheckService
from backend.app.camera.registry import CameraRegistry

__all__ = [
    "CameraAdapter",
    "CameraHealth",
    "CameraInfo",
    "CameraRegistry",
    "CaptureResult",
    "CaptureService",
    "DahuaCameraAdapter",
    "HealthCheckService",
]
