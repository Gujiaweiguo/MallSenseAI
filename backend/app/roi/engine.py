"""ROI geometry engine — stateless utility for all ROI geometric operations.

All coordinates are in normalized [0.0, 1.0] space. No pixel coordinates,
no DB dependencies.
"""

from __future__ import annotations

from typing import Union  # noqa: UP007 — Python 3.10 compat

from shapely.geometry import MultiPolygon as ShapelyMultiPolygon
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import Point as ShapelyPoint

from shared.coordinate_standard import Point


def _to_shapely(polygon: list[Point]) -> ShapelyPolygon:
    """Convert a list of normalized points to a Shapely Polygon."""
    if len(polygon) < 3:
        raise ValueError(f"Need at least 3 points for a polygon, got {len(polygon)}")
    return ShapelyPolygon(polygon)


class ROIEngine:
    """Stateless geometry utility for ROI operations.

    All methods are class methods or static. Use directly without
    instantiation: ``ROIEngine.point_in_polygon(...)``.
    """

    # ------------------------------------------------------------------
    # Core geometry
    # ------------------------------------------------------------------

    @staticmethod
    def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
        """Test whether *point* lies inside *polygon*.

        Uses the ray-casting algorithm via Shapely. Boundary points
        (exactly on an edge) return ``True``.
        """
        return ShapelyPoint(point).within(_to_shapely(polygon)) or ShapelyPoint(
            point
        ).touches(_to_shapely(polygon))

    @staticmethod
    def polygon_area(polygon: list[Point]) -> float:
        """Return the area of *polygon* in normalized square units."""
        return float(_to_shapely(polygon).area)

    @staticmethod
    def polygon_intersection(
        polygon1: list[Point], polygon2: list[Point]
    ) -> list[Point] | None:
        """Compute the intersection of two polygons.

        Returns the intersection vertices, or ``None`` if the polygons
        do not overlap.
        """
        sp1 = _to_shapely(polygon1)
        sp2 = _to_shapely(polygon2)
        result = sp1.intersection(sp2)
        if result.is_empty:
            return None
        if isinstance(result, ShapelyPolygon):
            # Exclude the closing repeated point that Shapely appends
            coords = list(result.exterior.coords[:-1])
            return [(float(x), float(y)) for x, y in coords]
        # MultiPolygon or other geometry — return largest polygon
        if isinstance(result, ShapelyMultiPolygon):
            largest = max(result.geoms, key=lambda g: g.area)
            coords = list(largest.exterior.coords[:-1])
            return [(float(x), float(y)) for x, y in coords]
        return None

    @staticmethod
    def polygon_union_area(polygon1: list[Point], polygon2: list[Point]) -> float:
        """Return the area of the union of two polygons."""
        sp1 = _to_shapely(polygon1)
        sp2 = _to_shapely(polygon2)
        return float(sp1.union(sp2).area)

    @staticmethod
    def iou(polygon1: list[Point], polygon2: list[Point]) -> float:
        """Intersection-over-Union of two polygons.

        Returns 0.0 if neither polygon has area or they don't overlap.
        """
        sp1 = _to_shapely(polygon1)
        sp2 = _to_shapely(polygon2)
        inter = sp1.intersection(sp2)
        union = sp1.union(sp2)
        if union.area == 0:
            return 0.0
        return float(inter.area / union.area)

    # ------------------------------------------------------------------
    # Obstruction-specific helpers
    # ------------------------------------------------------------------

    @staticmethod
    def occupied_area_ratio(
        zone_polygon: list[Point],
        obstacle_polygon: list[Point],
    ) -> float:
        """Ratio of *zone_polygon* covered by *obstacle_polygon*.

        Returns a value in [0.0, 1.0]. Returns 0.0 if the zone has
        zero area.
        """
        zone = _to_shapely(zone_polygon)
        obstacle = _to_shapely(obstacle_polygon)
        if zone.area == 0:
            return 0.0
        overlap = zone.intersection(obstacle)
        return float(overlap.area / zone.area)

    @staticmethod
    def remaining_clear_width(
        zone_polygon: list[Point],
        obstacle_polygon: list[Point],
        direction: str = "horizontal",
    ) -> float:
        """Width of the narrowest clear passage through *zone_polygon*
        after subtracting *obstacle_polygon*.

        Args:
            zone_polygon: The passable zone in normalized coords.
            obstacle_polygon: The obstacle blocking part of the zone.
            direction: ``"horizontal"`` measures left-to-right clear
                span; ``"vertical"`` measures top-to-bottom.

        Returns:
            The narrowest continuous clear span in normalized units.
            Returns the full zone span if no obstacle intersection.
        """
        zone = _to_shapely(zone_polygon)
        obstacle = _to_shapely(obstacle_polygon)
        clear = zone.difference(obstacle)

        if clear.is_empty:
            return 0.0

        if direction == "vertical":
            # Project onto Y axis
            bounds = zone.bounds  # (minx, miny, maxx, maxy)
            zone_span = bounds[3] - bounds[1]
            if zone_span == 0:
                return 0.0
            # Sample columns across the zone width and measure clear height
            min_x = bounds[0]
            max_x = bounds[2]
            step = (max_x - min_x) / 50 if (max_x - min_x) > 0 else 0.01
            min_clear = zone_span
            x = min_x
            while x <= max_x:
                col_line = ShapelyPolygon(
                    [(x, bounds[1]), (x, bounds[3]), (x + step / 2, bounds[3]), (x + step / 2, bounds[1])]
                )
                col_clear = clear.intersection(col_line)
                if not col_clear.is_empty:
                    col_bounds = col_clear.bounds
                    span = col_bounds[3] - col_bounds[1]
                    if span < min_clear:
                        min_clear = span
                x += step
            return float(min_clear)
        else:
            # Horizontal — project onto X axis
            bounds = zone.bounds
            zone_span = bounds[2] - bounds[0]
            if zone_span == 0:
                return 0.0
            min_y = bounds[1]
            max_y = bounds[3]
            step = (max_y - min_y) / 50 if (max_y - min_y) > 0 else 0.01
            min_clear = zone_span
            y = min_y
            while y <= max_y:
                row_line = ShapelyPolygon(
                    [(bounds[0], y), (bounds[2], y), (bounds[2], y + step / 2), (bounds[0], y + step / 2)]
                )
                row_clear = clear.intersection(row_line)
                if not row_clear.is_empty:
                    row_bounds = row_clear.bounds
                    span = row_bounds[2] - row_bounds[0]
                    if span < min_clear:
                        min_clear = span
                y += step
            return float(min_clear)

    @staticmethod
    def is_in_forbidden_zone(
        point_or_polygon: Union[Point, list[Point]],
        forbidden_zone_polygon: list[Point],
    ) -> bool:
        """Check if a point or polygon overlaps with a forbidden zone.

        Args:
            point_or_polygon: Either a single ``(x, y)`` point or a
                list of polygon vertices to test.
            forbidden_zone_polygon: The forbidden zone boundary.

        Returns:
            ``True`` if the test geometry touches or is within the
            forbidden zone.
        """
        forbidden = _to_shapely(forbidden_zone_polygon)

        if isinstance(point_or_polygon, list) and len(point_or_polygon) >= 1:
            # Heuristic: list of tuples → polygon
            if isinstance(point_or_polygon[0], (list, tuple)):
                if len(point_or_polygon) >= 3:
                    test = _to_shapely(point_or_polygon)  # type: ignore[arg-type]
                else:
                    # Treat as a collection of points — any hits?
                    return any(
                        ShapelyPoint(pt).within(forbidden)
                        or ShapelyPoint(pt).touches(forbidden)
                        for pt in point_or_polygon
                    )
            else:
                # Single point passed as tuple (x, y) but typed as list —
                # this shouldn't happen due to type narrowing, but guard anyway
                return bool(
                    ShapelyPoint(point_or_polygon).within(forbidden)
                    or ShapelyPoint(point_or_polygon).touches(forbidden)
                )
        else:
            # Single point
            test = ShapelyPoint(point_or_polygon)

        return bool(test.intersects(forbidden))
