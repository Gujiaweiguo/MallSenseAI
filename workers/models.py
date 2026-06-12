"""Worker-internal data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class WorkerStatus(str, Enum):
    """Lifecycle states for the inspection worker."""

    idle = "idle"
    running = "running"
    stopping = "stopping"
    stopped = "stopped"
    error = "error"


@dataclass(slots=True)
class InspectionResult:
    """Outcome of one camera inspection capture."""

    camera_id: int
    success: bool
    image_bytes: bytes | None
    error: str | None
    duration_ms: float
    timestamp: datetime


@dataclass(slots=True)
class WorkerMetrics:
    """Aggregate worker health counters."""

    total_inspections: int = 0
    successful: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0
    last_run_at: datetime | None = None
    cameras_active: int = 0


@dataclass(slots=True)
class CameraInspectionMetrics:
    """Per-camera inspection counters and health signals."""

    camera_id: int
    total: int = 0
    successful: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0


@dataclass(slots=True)
class ScheduledCamera:
    """In-memory scheduler state for one camera."""

    camera_id: int
    interval_seconds: float
    next_run_at: float
    consecutive_failures: int = 0
    running: bool = False
