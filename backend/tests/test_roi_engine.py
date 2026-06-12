from __future__ import annotations

import pytest

from backend.app.roi.engine import ROIEngine
from backend.app.roi.validation import validate_polygon, validate_rect
from shared.coordinate_standard import (
    legacy_1000x750_to_normalized,
    legacy_1600x1200_to_normalized,
    normalized_to_pixel,
    pixel_to_normalized,
)


# ---------------------------------------------------------------------------
# ROIEngine core geometry
# ---------------------------------------------------------------------------


class TestPointInPolygon:
    def test_inside_triangle(self):
        tri = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        assert ROIEngine.point_in_polygon((0.5, 0.3), tri) is True

    def test_outside_triangle(self):
        tri = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        assert ROIEngine.point_in_polygon((0.9, 0.9), tri) is False

    def test_on_edge(self):
        tri = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        assert ROIEngine.point_in_polygon((0.5, 0.0), tri) is True

    def test_inside_rectangle(self):
        rect = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
        assert ROIEngine.point_in_polygon((0.5, 0.5), rect) is True

    def test_outside_rectangle(self):
        rect = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
        assert ROIEngine.point_in_polygon((0.1, 0.1), rect) is False

    def test_inside_concave(self):
        concave = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.5, 0.5), (0.0, 1.0)]
        assert ROIEngine.point_in_polygon((0.2, 0.2), concave) is True

    def test_outside_concave_notch(self):
        concave = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.5, 0.5), (0.0, 1.0)]
        assert ROIEngine.point_in_polygon((0.9, 0.9), concave) is True  # in right lobe


class TestPolygonArea:
    def test_unit_square(self):
        square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert ROIEngine.polygon_area(square) == pytest.approx(1.0)

    def test_triangle(self):
        tri = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        assert ROIEngine.polygon_area(tri) == pytest.approx(0.5)

    def test_small_rectangle(self):
        rect = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
        assert ROIEngine.polygon_area(rect) == pytest.approx(0.36)

    def test_too_few_points_raises(self):
        with pytest.raises(ValueError):
            ROIEngine.polygon_area([(0.0, 0.0), (1.0, 0.0)])

    def test_degenerate_collinear_area_is_zero(self):
        area = ROIEngine.polygon_area([(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)])
        assert area == pytest.approx(0.0)


class TestPolygonIntersection:
    def test_overlapping_rectangles(self):
        r1 = [(0.0, 0.0), (0.6, 0.0), (0.6, 0.6), (0.0, 0.6)]
        r2 = [(0.4, 0.4), (1.0, 0.4), (1.0, 1.0), (0.4, 1.0)]
        result = ROIEngine.polygon_intersection(r1, r2)
        assert result is not None
        assert len(result) >= 3

    def test_no_overlap(self):
        r1 = [(0.0, 0.0), (0.3, 0.0), (0.3, 0.3), (0.0, 0.3)]
        r2 = [(0.7, 0.7), (1.0, 0.7), (1.0, 1.0), (0.7, 1.0)]
        assert ROIEngine.polygon_intersection(r1, r2) is None

    def test_contained(self):
        outer = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        inner = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
        result = ROIEngine.polygon_intersection(outer, inner)
        assert result is not None
        assert len(result) >= 3


class TestIoU:
    def test_identical_polygons(self):
        poly = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert ROIEngine.iou(poly, poly) == pytest.approx(1.0)

    def test_no_overlap(self):
        r1 = [(0.0, 0.0), (0.3, 0.0), (0.3, 0.3), (0.0, 0.3)]
        r2 = [(0.7, 0.7), (1.0, 0.7), (1.0, 1.0), (0.7, 1.0)]
        assert ROIEngine.iou(r1, r2) == pytest.approx(0.0)

    def test_partial_overlap(self):
        r1 = [(0.0, 0.0), (0.6, 0.0), (0.6, 0.6), (0.0, 0.6)]
        r2 = [(0.4, 0.4), (1.0, 0.4), (1.0, 1.0), (0.4, 1.0)]
        iou = ROIEngine.iou(r1, r2)
        assert 0.0 < iou < 1.0


class TestOccupiedAreaRatio:
    def test_half_covered(self):
        zone = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        obstacle = [(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)]
        assert ROIEngine.occupied_area_ratio(zone, obstacle) == pytest.approx(0.5)

    def test_no_obstacle_overlap(self):
        zone = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]
        obstacle = [(0.7, 0.7), (1.0, 0.7), (1.0, 1.0), (0.7, 1.0)]
        assert ROIEngine.occupied_area_ratio(zone, obstacle) == pytest.approx(0.0)

    def test_zero_area_zone(self):
        zone = [(0.0, 0.0), (1.0, 0.0), (1.0, 0.0)]
        obstacle = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert ROIEngine.occupied_area_ratio(zone, obstacle) == 0.0


class TestRemainingClearWidth:
    def test_no_obstacle(self):
        zone = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        obstacle = [(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 3.0)]
        width = ROIEngine.remaining_clear_width(zone, obstacle)
        assert width > 0.9

    def test_fully_blocked(self):
        zone = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        obstacle = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        width = ROIEngine.remaining_clear_width(zone, obstacle)
        assert width == pytest.approx(0.0)


class TestIsInForbiddenZone:
    def test_point_inside(self):
        zone = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert ROIEngine.is_in_forbidden_zone((0.5, 0.5), zone) is True

    def test_point_outside(self):
        zone = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]
        assert ROIEngine.is_in_forbidden_zone((0.8, 0.8), zone) is False

    def test_polygon_overlaps(self):
        zone = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]
        test_poly = [(0.3, 0.3), (0.8, 0.3), (0.8, 0.8), (0.3, 0.8)]
        assert ROIEngine.is_in_forbidden_zone(test_poly, zone) is True

    def test_polygon_no_overlap(self):
        zone = [(0.0, 0.0), (0.3, 0.0), (0.3, 0.3), (0.0, 0.3)]
        test_poly = [(0.7, 0.7), (1.0, 0.7), (1.0, 1.0), (0.7, 1.0)]
        assert ROIEngine.is_in_forbidden_zone(test_poly, zone) is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidatePolygon:
    def test_valid_triangle(self):
        result = validate_polygon([(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)])
        assert result.valid is True
        assert len(result.errors) == 0

    def test_too_few_points(self):
        result = validate_polygon([(0.0, 0.0), (1.0, 0.0)])
        assert result.valid is False
        assert "at least 3" in result.errors[0]

    def test_zero_points(self):
        result = validate_polygon([])
        assert result.valid is False

    def test_out_of_range_coordinates(self):
        result = validate_polygon([(0.0, 0.0), (1.5, 0.0), (0.5, 1.0)])
        assert result.valid is False
        assert any("outside" in e for e in result.errors)

    def test_collinear_points_invalid_polygon(self):
        result = validate_polygon([(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)])
        assert result.valid is False

    def test_self_intersecting(self):
        bowtie = [(0.0, 0.0), (1.0, 1.0), (1.0, 0.0), (0.0, 1.0)]
        result = validate_polygon(bowtie)
        assert result.valid is False

    def test_bool_conversion(self):
        result = validate_polygon([(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)])
        assert bool(result) is True


class TestValidateRect:
    def test_valid_rect(self):
        result = validate_rect(0.1, 0.1, 0.5, 0.5)
        assert result.valid is True

    def test_zero_width(self):
        result = validate_rect(0.1, 0.1, 0.0, 0.5)
        assert result.valid is False

    def test_negative_height(self):
        result = validate_rect(0.1, 0.1, 0.5, -0.1)
        assert result.valid is False

    def test_extends_beyond_boundary(self):
        result = validate_rect(0.8, 0.8, 0.5, 0.5)
        assert result.valid is False


# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------


class TestPixelToNormalized:
    def test_polygon_center(self):
        result = pixel_to_normalized(1000, 750, [(500.0, 375.0)], "polygon")
        assert result["type"] == "polygon"
        assert result["points"][0] == pytest.approx((0.5, 0.5))

    def test_rect_full_image(self):
        result = pixel_to_normalized(1000, 750, (0.0, 0.0, 1000.0, 750.0), "rect")
        assert result["type"] == "rect"
        assert result["width"] == pytest.approx(1.0)
        assert result["height"] == pytest.approx(1.0)

    def test_zero_dimension_raises(self):
        with pytest.raises(ValueError):
            pixel_to_normalized(0, 750, [(100.0, 100.0)], "polygon")

    def test_clamps_oversized(self):
        result = pixel_to_normalized(1000, 750, [(1500.0, 1000.0)], "polygon")
        assert result["points"][0][0] <= 1.0
        assert result["points"][0][1] <= 1.0


class TestNormalizedToPixel:
    def test_roundtrip_polygon(self):
        original = [(100.0, 200.0), (300.0, 400.0)]
        normalized = pixel_to_normalized(1000, 750, original, "polygon")
        back = normalized_to_pixel(1000, 750, normalized)
        assert len(back) == 2
        for orig, rt in zip(original, back):
            assert orig[0] == pytest.approx(rt[0], abs=2)
            assert orig[1] == pytest.approx(rt[1], abs=2)

    def test_roundtrip_rect(self):
        original = (100.0, 100.0, 200.0, 150.0)
        normalized = pixel_to_normalized(1000, 750, original, "rect")
        back = normalized_to_pixel(1000, 750, normalized)
        assert back[0] == pytest.approx(100, abs=2)
        assert back[1] == pytest.approx(100, abs=2)


class TestLegacyConversion:
    def test_1000x750(self):
        result = legacy_1000x750_to_normalized([(500.0, 375.0)])
        assert result["points"][0] == pytest.approx((0.5, 0.5))

    def test_1600x1200(self):
        result = legacy_1600x1200_to_normalized([(800.0, 600.0)])
        assert result["points"][0] == pytest.approx((0.5, 0.5))
