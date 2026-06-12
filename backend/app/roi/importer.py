"""Legacy ROI importer — converts safe_zones.json data to normalized geometry.

Handles three known legacy formats from ``safe_zones.json``:
1. Real polygons with actual pixel coordinates
2. Degenerate all-zeros polygons (marked ``degenerate=True``)
3. Near-zero corrupted data (marked with warnings)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.coordinate_standard import (
    LEGACY_RUNTIME_HEIGHT,
    LEGACY_RUNTIME_WIDTH,
    Geometry,
    Point,
    pixel_to_normalized,
)


@dataclass
class ImportedROI:
    """A single ROI imported from legacy safe_zones data."""

    zone_type: str
    geometry: Geometry
    source_data: list[Point]
    degenerate: bool = False
    warnings: list[str] = field(default_factory=list)


def _is_all_zeros(points: list[list[float]]) -> bool:
    """Check if all coordinate values are exactly zero."""
    return all(abs(x) < 1e-9 and abs(y) < 1e-9 for x, y in points)


def _is_near_zero(points: list[list[float]], threshold: float = 1.0) -> bool:
    """Check if all coordinates are suspiciously close to the origin.

    A polygon whose every vertex lies within *threshold* pixels of
    ``(0, 0)`` is almost certainly corrupted data, not a real zone.
    """
    return all(abs(x) <= threshold and abs(y) <= threshold for x, y in points)


def _has_enough_points(points: list[list[float]]) -> bool:
    """A valid polygon needs at least 3 unique-ish points."""
    return len(points) >= 3


def import_legacy_safe_zones(
    safe_zones_data: list[dict[str, Any]],
    source_width: int = LEGACY_RUNTIME_WIDTH,
    source_height: int = LEGACY_RUNTIME_HEIGHT,
) -> list[ImportedROI]:
    """Import legacy safe_zones entries into normalized ROI geometry.

    Args:
        safe_zones_data: List of dicts from ``safe_zones.json``. Each
            entry is expected to have ``"type"`` and ``"data"`` keys.
            Example: ``{"type": "polygon", "data": [[x, y], ...]}``
        source_width: Width of the legacy coordinate space (default 1000).
        source_height: Height of the legacy coordinate space (default 750).

    Returns:
        List of :class:`ImportedROI` instances with normalized geometry.
    """
    results: list[ImportedROI] = []

    for entry in safe_zones_data:
        zone_type: str = entry.get("type", "polygon")
        raw_points: list[list[float]] = entry.get("data", [])

        warnings: list[str] = []

        # --- degenerate all-zeros ---
        if _is_all_zeros(raw_points):
            normalized_pts: list[Point] = [(0.0, 0.0)] * max(len(raw_points), 3)
            geometry: Geometry = {"type": "polygon", "points": normalized_pts}
            results.append(
                ImportedROI(
                    zone_type=zone_type,
                    geometry=geometry,
                    source_data=[(float(p[0]), float(p[1])) for p in raw_points],
                    degenerate=True,
                    warnings=["All coordinates are zero — degenerate zone"],
                )
            )
            continue

        # --- near-zero corrupted ---
        if _is_near_zero(raw_points):
            normalized_pts = [
                (float(p[0] / source_width), float(p[1] / source_height))
                for p in raw_points
            ]
            geometry = {"type": "polygon", "points": normalized_pts}
            results.append(
                ImportedROI(
                    zone_type=zone_type,
                    geometry=geometry,
                    source_data=[(float(p[0]), float(p[1])) for p in raw_points],
                    degenerate=False,
                    warnings=[
                        f"All coordinates within 1px of origin — possibly corrupted"
                    ],
                )
            )
            continue

        # --- not enough points ---
        if not _has_enough_points(raw_points):
            results.append(
                ImportedROI(
                    zone_type=zone_type,
                    geometry={
                        "type": "polygon",
                        "points": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)],
                    },
                    source_data=[(float(p[0]), float(p[1])) for p in raw_points],
                    degenerate=True,
                    warnings=[
                        f"Only {len(raw_points)} points — need at least 3 for a polygon"
                    ],
                )
            )
            continue

        # --- normal polygon ---
        source_tuples = [(float(p[0]), float(p[1])) for p in raw_points]
        normalized = pixel_to_normalized(
            source_width, source_height, source_tuples, "polygon"
        )
        results.append(
            ImportedROI(
                zone_type=zone_type,
                geometry=normalized,
                source_data=source_tuples,
                degenerate=False,
                warnings=warnings,
            )
        )

    return results
