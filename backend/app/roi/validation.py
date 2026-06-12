"""ROI geometry validation — polygon and rect checks in normalized [0, 1] space."""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely.geometry import Polygon


@dataclass
class ValidationResult:
    """Result of validating a geometric primitive."""

    valid: bool
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


def validate_polygon(points: list[tuple[float, float]]) -> ValidationResult:
    """Validate a polygon in normalized [0, 1] coordinate space.

    Checks:
    - At least 3 points
    - All coordinates in [0, 1]
    - Points are not collinear (area > 0)
    - No self-intersection
    """
    errors: list[str] = []

    # --- minimum vertex count ---
    if len(points) < 3:
        errors.append(f"Polygon must have at least 3 points, got {len(points)}")
        return ValidationResult(valid=False, errors=errors)

    # --- coordinate range ---
    for i, (x, y) in enumerate(points):
        if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
            errors.append(
                f"Point {i} ({x}, {y}) is outside the normalized [0, 1] range"
            )

    # --- collinearity (degenerate polygon) ---
    if len(points) >= 3:
        try:
            poly = Polygon(points)
            if poly.is_valid and poly.area == 0.0:
                errors.append("Polygon points are collinear — resulting area is zero")
        except Exception:
            pass  # Shapely will also catch degenerate input

    # --- self-intersection ---
    if len(points) >= 3:
        try:
            poly = Polygon(points)
            if not poly.is_valid:
                errors.append(
                    f"Polygon is self-intersecting or otherwise invalid (Shapely reason: {poly.is_valid})"
                )
        except Exception as exc:
            errors.append(f"Failed to construct polygon for validation: {exc}")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_rect(x: float, y: float, w: float, h: float) -> ValidationResult:
    """Validate a rectangle in normalized [0, 1] coordinate space.

    Checks:
    - Width and height are positive
    - Rectangle fits within [0, 1]
    """
    errors: list[str] = []

    if w <= 0:
        errors.append(f"Rectangle width must be positive, got {w}")
    if h <= 0:
        errors.append(f"Rectangle height must be positive, got {h}")

    if x < 0.0 or y < 0.0:
        errors.append(f"Rectangle origin ({x}, {y}) is outside [0, 1] range")

    if x + w > 1.0:
        errors.append(
            f"Rectangle extends beyond x=1.0 (x={x}, width={w}, x+w={x + w})"
        )
    if y + h > 1.0:
        errors.append(
            f"Rectangle extends beyond y=1.0 (y={y}, height={h}, y+h={y + h})"
        )

    return ValidationResult(valid=len(errors) == 0, errors=errors)
