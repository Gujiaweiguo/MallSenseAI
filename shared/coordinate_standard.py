from __future__ import annotations

from typing import Literal, TypedDict, overload

LEGACY_RUNTIME_WIDTH = 1000
LEGACY_RUNTIME_HEIGHT = 750
LEGACY_MANAGER_WIDTH = 1600
LEGACY_MANAGER_HEIGHT = 1200

Point = tuple[float, float]
PixelPoint = tuple[int, int]
ZoneType = Literal["polygon", "rect"]


class PolygonGeometry(TypedDict):
    type: Literal["polygon"]
    points: list[Point]


class RectGeometry(TypedDict):
    type: Literal["rect"]
    x: float
    y: float
    width: float
    height: float


Geometry = PolygonGeometry | RectGeometry


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_point(width: int, height: int, point: tuple[float, float]) -> Point:
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    return (_clamp(point[0] / width), _clamp(point[1] / height))


def _pixel_point(width: int, height: int, point: tuple[float, float]) -> PixelPoint:
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    return (round(_clamp(point[0]) * width), round(_clamp(point[1]) * height))


@overload
def pixel_to_normalized(width: int, height: int, coords: list[tuple[float, float]], zone_type: Literal["polygon"] = "polygon") -> PolygonGeometry: ...


@overload
def pixel_to_normalized(width: int, height: int, coords: tuple[float, float, float, float], zone_type: Literal["rect"]) -> RectGeometry: ...


def pixel_to_normalized(
    width: int,
    height: int,
    coords: list[tuple[float, float]] | tuple[float, float, float, float],
    zone_type: ZoneType = "polygon",
) -> Geometry:
    """Convert legacy pixel-space polygon or rect coordinates to normalized geometry."""
    if zone_type == "polygon":
        if not isinstance(coords, list):
            raise TypeError("polygon coordinates must be a list of points")
        return {"type": "polygon", "points": [_normalize_point(width, height, point) for point in coords]}
    if not isinstance(coords, tuple) or len(coords) != 4:
        raise TypeError("rect coordinates must be a 4-tuple: (x, y, width, height)")
    x, y, rect_width, rect_height = coords
    start = _normalize_point(width, height, (x, y))
    end = _normalize_point(width, height, (x + rect_width, y + rect_height))
    return {"type": "rect", "x": start[0], "y": start[1], "width": max(0.0, end[0] - start[0]), "height": max(0.0, end[1] - start[1])}


@overload
def normalized_to_pixel(width: int, height: int, coords: PolygonGeometry) -> list[PixelPoint]: ...


@overload
def normalized_to_pixel(width: int, height: int, coords: RectGeometry) -> tuple[int, int, int, int]: ...


def normalized_to_pixel(width: int, height: int, coords: Geometry) -> list[PixelPoint] | tuple[int, int, int, int]:
    """Convert normalized geometry back to pixel coordinates for legacy renderers."""
    if coords["type"] == "polygon":
        return [_pixel_point(width, height, point) for point in coords["points"]]
    x1, y1 = _pixel_point(width, height, (coords["x"], coords["y"]))
    x2, y2 = _pixel_point(width, height, (coords["x"] + coords["width"], coords["y"] + coords["height"]))
    return (x1, y1, max(0, x2 - x1), max(0, y2 - y1))


def legacy_1000x750_to_normalized(coords: list[tuple[float, float]] | tuple[float, float, float, float], zone_type: ZoneType = "polygon") -> Geometry:
    if zone_type == "polygon":
        if not isinstance(coords, list):
            raise TypeError("polygon coordinates must be a list of points")
        return pixel_to_normalized(LEGACY_RUNTIME_WIDTH, LEGACY_RUNTIME_HEIGHT, coords, "polygon")
    if not isinstance(coords, tuple):
        raise TypeError("rect coordinates must be a 4-tuple")
    return pixel_to_normalized(LEGACY_RUNTIME_WIDTH, LEGACY_RUNTIME_HEIGHT, coords, "rect")


def legacy_1600x1200_to_normalized(coords: list[tuple[float, float]] | tuple[float, float, float, float], zone_type: ZoneType = "polygon") -> Geometry:
    if zone_type == "polygon":
        if not isinstance(coords, list):
            raise TypeError("polygon coordinates must be a list of points")
        return pixel_to_normalized(LEGACY_MANAGER_WIDTH, LEGACY_MANAGER_HEIGHT, coords, "polygon")
    if not isinstance(coords, tuple):
        raise TypeError("rect coordinates must be a 4-tuple")
    return pixel_to_normalized(LEGACY_MANAGER_WIDTH, LEGACY_MANAGER_HEIGHT, coords, "rect")
