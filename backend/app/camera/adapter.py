"""Camera adapter abstraction and Dahua implementation."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class HealthStatus(str, Enum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


@dataclass
class CameraHealth:
    """Runtime health information for a camera."""

    status: HealthStatus = HealthStatus.online
    last_capture_at: float | None = None  # unix timestamp
    consecutive_failures: int = 0
    latency_ms: float = 0.0


@dataclass
class CameraInfo:
    """Static metadata identifying a camera."""

    ip: str
    port: int
    username: str
    location: str = ""


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class CameraAdapter(ABC):
    """Unified interface that all camera vendors must implement."""

    @abstractmethod
    async def capture_snapshot(self) -> bytes:
        """Capture a single JPEG snapshot. Returns raw JPEG bytes."""

    @abstractmethod
    async def check_health(self) -> CameraHealth:
        """Probe the camera and return current health status."""

    @abstractmethod
    def get_camera_info(self) -> CameraInfo:
        """Return static camera metadata (no I/O)."""

    def get_health(self) -> CameraHealth:
        """Return the most-recently computed health snapshot (no I/O).

        Default implementation returns a fresh *online* health; concrete
        adapters override this to expose their tracked state.
        """
        return CameraHealth()


# ---------------------------------------------------------------------------
# Dahua implementation
# ---------------------------------------------------------------------------

# Snapshot URL paths tried in order (mirrors legacy camera.py).
_DAHUA_SNAPSHOT_PATHS: list[str] = [
    "/cgi-bin/snapshot.cgi",
    "/cgi-bin/api.cgi?cmd=Snap&channel=0&rs=wuuPhkmUCeI9WG7C",
    "/cgi-bin/api.cgi?cmd=Snap&channel=1&rs=wuuPhkmUCeI9WG7C",
    "/snapshot.jpg",
    "/cgi-bin/snapshot.cgi?channel=1",
    "/cgi-bin/snapshot.cgi?channel=0",
    "/cgi-bin/webgrab.cgi",
    "/cgi-bin/encoder/snapshot.cgi",
    "/cgi-bin/encoder/snapshot.cgi?channel=0",
]


class DahuaCameraAdapter(CameraAdapter):
    """Concrete adapter for Dahua IP cameras using HTTP digest auth."""

    def __init__(
        self,
        ip: str,
        port: int = 80,
        username: str = "admin",
        password: str = "",
        location: str = "",
        *,
        timeout: float = 10.0,
    ) -> None:
        self._info = CameraInfo(ip=ip, port=port, username=username, location=location)
        self._password = password
        self._timeout = timeout
        self._base_url = f"http://{ip}:{port}"
        self._health = CameraHealth()

    # -- public interface ---------------------------------------------------

    async def capture_snapshot(self) -> bytes:
        """Try each Dahua snapshot path until one returns valid JPEG bytes."""
        start = time.monotonic()
        last_exc: Exception | None = None

        async with httpx.AsyncClient(
            auth=httpx.DigestAuth(self._info.username, self._password),
            timeout=httpx.Timeout(self._timeout, connect=self._timeout),
            verify=False,
        ) as client:
            for path in _DAHUA_SNAPSHOT_PATHS:
                url = f"{self._base_url}{path}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "")
                        body = resp.content
                        if self._looks_like_jpeg(body, content_type):
                            elapsed_ms = (time.monotonic() - start) * 1000
                            self._record_success(elapsed_ms)
                            logger.debug(
                                "Dahua snapshot OK via %s (%.0f ms)", path, elapsed_ms
                            )
                            return body
                except Exception as exc:
                    last_exc = exc
                    logger.debug("Dahua path %s failed: %s", path, exc)
                    continue

        self._record_failure()
        raise CameraCaptureError(
            f"All Dahua snapshot paths failed for {self._info.ip}"
        ) from last_exc

    async def check_health(self) -> CameraHealth:
        """Lightweight HTTP probe — try the first snapshot path with a short timeout."""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                auth=httpx.DigestAuth(self._info.username, self._password),
                timeout=httpx.Timeout(self._timeout, connect=min(self._timeout, 5.0)),
                verify=False,
            ) as client:
                url = f"{self._base_url}{_DAHUA_SNAPSHOT_PATHS[0]}"
                resp = await client.get(url)
                elapsed_ms = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    self._record_success(elapsed_ms)
                else:
                    self._record_failure()
        except Exception:
            logger.warning("Capture attempt failed", exc_info=True)
            self._record_failure()
        return self._health

    def get_camera_info(self) -> CameraInfo:
        return self._info

    def get_health(self) -> CameraHealth:
        return self._health

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _looks_like_jpeg(body: bytes, content_type: str) -> bool:
        """Heuristic: either the content-type says image/* or the payload is a reasonable size."""
        if content_type.startswith("image/"):
            return True
        return 1000 < len(body) < 10_000_000

    def _record_success(self, latency_ms: float) -> None:
        self._health.status = HealthStatus.online
        self._health.last_capture_at = time.time()
        self._health.consecutive_failures = 0
        self._health.latency_ms = latency_ms

    def _record_failure(self) -> None:
        self._health.consecutive_failures += 1
        self._health.last_capture_at = time.time()
        if self._health.consecutive_failures >= 5:
            self._health.status = HealthStatus.offline
        else:
            self._health.status = HealthStatus.degraded


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CameraCaptureError(RuntimeError):
    """Raised when a snapshot cannot be obtained from the camera."""
