"""Base detector interface — shared contract for all anomaly detectors.

Every detector in the platform must subclass ``BaseDetector`` and implement
:meth:`detect`.  Results use normalised ``[0.0, 1.0]`` coordinates so they
are independent of image resolution.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from shared.coordinate_standard import Point


@dataclass(frozen=True)
class DetectionResult:
    """A single detection produced by a detector.

    Attributes:
        polygon: Bounding polygon in normalised ``[0.0, 1.0]`` coordinates.
            Typically a 4-point rectangle
            ``(x1, y1), (x2, y1), (x2, y2), (x1, y2)``.
        confidence: Detection confidence in ``[0.0, 1.0]``.
        label: Human-readable label for the detected class
            (e.g. ``"bottle"``, ``"trash"``).
        metadata: Arbitrary extra information (area ratio, class id, etc.).
    """

    polygon: list[Point]
    confidence: float
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseDetector(abc.ABC):
    """Abstract base for all anomaly detectors.

    Subclasses must implement :meth:`detect` and :attr:`is_enabled`.
    """

    @property
    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """Return ``True`` when the detector is active and should be called."""

    @abc.abstractmethod
    async def detect(
        self,
        image_bytes: bytes,
        roi_polygons: list[list[Point]],
        config: dict[str, Any],
    ) -> list[DetectionResult]:
        """Run detection on *image_bytes*, constrained to *roi_polygons*.

        Args:
            image_bytes: Raw JPEG/PNG bytes from the camera snapshot.
            roi_polygons: Zero or more floor-zone polygons in normalised
                coordinates.  Detections outside every polygon are discarded.
            config: Detector-specific configuration (confidence threshold,
                class allow-list, etc.).

        Returns:
            List of :class:`DetectionResult` instances, each fully inside
            at least one ROI polygon.  Empty list when nothing is detected.
        """
