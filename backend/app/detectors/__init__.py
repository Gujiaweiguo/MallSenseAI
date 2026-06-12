"""Detector package — anomaly detection abstractions and implementations."""

from __future__ import annotations

from backend.app.detectors.base import BaseDetector, DetectionResult
from backend.app.detectors.debris import DebrisDetector
from backend.app.detectors.fire_smoke import FireSmokeDetector
from backend.app.detectors.integration import DetectorRegistry

__all__ = [
    "BaseDetector",
    "DebrisDetector",
    "DetectorRegistry",
    "DetectionResult",
    "FireSmokeDetector",
]
