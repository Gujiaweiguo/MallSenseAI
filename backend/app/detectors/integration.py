"""Detector registry — centralised registry for all anomaly detectors.

Provides a single point where detector instances are registered by type
string (``"obstruction"``, ``"debris"``, ``"fire_smoke"``) so that the
inspection worker can look them up without importing concrete classes.
"""

from __future__ import annotations

import logging
from backend.app.detectors.base import BaseDetector

logger = logging.getLogger(__name__)


class DetectorRegistry:
    """Registry that maps detector type strings to :class:`BaseDetector` instances.

    Typical usage::

        registry = DetectorRegistry()
        registry.register("debris", DebrisDetector())
        ...
        detector = registry.get_detector("debris")
        results = await detector.detect(image_bytes, rois, config)
    """

    def __init__(self) -> None:
        self._detectors: dict[str, BaseDetector] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, detector_type: str, detector: BaseDetector) -> None:
        """Register a detector instance under *detector_type*.

        If a detector was already registered under the same key it is
        silently replaced (and a debug message is logged).
        """
        if detector_type in self._detectors:
            logger.debug(
                "DetectorRegistry: replacing existing detector for %r",
                detector_type,
            )
        self._detectors[detector_type] = detector
        logger.info(
            "DetectorRegistry: registered detector %r (%s)",
            detector_type,
            type(detector).__name__,
        )

    def get_detector(self, detector_type: str) -> BaseDetector | None:
        """Return the detector registered under *detector_type*, or ``None``."""
        return self._detectors.get(detector_type)

    def list_types(self) -> list[str]:
        """Return all registered detector type keys."""
        return list(self._detectors.keys())

    def enabled_types(self) -> list[str]:
        """Return detector types whose :attr:`is_enabled` is ``True``."""
        return [k for k, v in self._detectors.items() if v.is_enabled]

    def unregister(self, detector_type: str) -> None:
        """Remove a detector from the registry."""
        self._detectors.pop(detector_type, None)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __contains__(self, detector_type: str) -> bool:
        return detector_type in self._detectors

    def __len__(self) -> int:
        return len(self._detectors)

    def __repr__(self) -> str:
        types = ", ".join(self._detectors.keys())
        return f"DetectorRegistry([{types}])"


# Module-level singleton for convenience.
_global_registry: DetectorRegistry | None = None


def get_global_registry() -> DetectorRegistry:
    """Return the module-level :class:`DetectorRegistry` singleton.

    Creates it on first call.  Subsequent calls return the same instance.
    """
    global _global_registry  # noqa: PLW0603
    if _global_registry is None:
        _global_registry = DetectorRegistry()
    return _global_registry
