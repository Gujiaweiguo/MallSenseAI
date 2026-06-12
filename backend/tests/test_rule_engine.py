"""Comprehensive tests for the obstruction rule engine.

Covers:
- ObstructionRuleEngine: area, duration, forbidden-zone modes + edge cases
- CooldownTracker: time-based suppression, independence, cleanup
- AlertCandidate / RuleEvaluationResult: creation, immutability, field validation
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.models.entities import AlertSeverity, RuleType
from backend.app.rules import cooldown as cooldown_module
from backend.app.rules.config import ForbiddenZoneConfig, ObstructionAreaConfig, ObstructionDurationConfig
from backend.app.rules.cooldown import CooldownTracker
from backend.app.rules.engine import ActiveRule, Geometry, ObstructionRuleEngine, RectGeometry
from backend.app.rules.models import AlertCandidate, RuleEvaluationResult

Point = tuple[float, float]


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def roi_polygon() -> list[Point]:
    """A unit-square ROI covering [0,0]–[1,1]."""
    return [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def square(x1: float, y1: float, x2: float, y2: float) -> list[Point]:
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def make_rule(
    *,
    rule_id: int = 1,
    camera_id: int = 10,
    roi_id: int = 20,
    rule_type: RuleType | str = RuleType.obstruction_area,
    config: dict[str, object] | None = None,
    priority: int = 100,
    roi_geometry: Geometry | list[Point] | None = None,
) -> ActiveRule:
    default_geometry: RectGeometry = {"type": "rect", "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    return ActiveRule(
        rule_id=rule_id,
        camera_id=camera_id,
        roi_id=roi_id,
        roi_geometry=roi_geometry or default_geometry,
        rule_type=rule_type,
        config=config or {},
        priority=priority,
    )


def age_active_condition(rule: ActiveRule, cooldown_state: dict[int, float], seconds: float) -> None:
    """Rewind the 'first-seen' timestamp so the condition appears older."""
    active_key = ObstructionRuleEngine._active_key(rule.rule_id, rule.roi_id)
    cooldown_state[active_key] -= seconds


def set_last_alert(rule: ActiveRule, cooldown_state: dict[int, float], seconds_ago: float) -> None:
    """Set the last-alert timestamp to *now − seconds_ago*."""
    alert_key = ObstructionRuleEngine._alert_key(rule.rule_id, rule.roi_id)
    import time
    cooldown_state[alert_key] = time.time() - seconds_ago


# ===========================================================================
# ObstructionRuleEngine — Area mode
# ===========================================================================


class TestAreaMode:
    """Tests for obstruction_area rule type."""

    def test_triggers_when_obstruction_area_exceeds_threshold(self) -> None:
        rule = make_rule(config={"threshold_ratio": 0.25, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.6, 0.6)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.rule_type == RuleType.obstruction_area
        assert candidate.camera_id == 10
        assert candidate.roi_id == 20
        assert candidate.rule_id == 1
        assert candidate.evidence["obstacle_polygon"] == detection
        assert candidate.evidence["threshold"] == 0.25
        assert candidate.evidence["metric_value"] == pytest.approx(0.36)

    def test_does_not_trigger_below_threshold(self) -> None:
        rule = make_rule(config={"threshold_ratio": 0.5, "min_duration_seconds": 0, "cooldown_seconds": 0})

        candidates = ObstructionRuleEngine.evaluate(10, [square(0.0, 0.0, 0.4, 0.4)], [rule], {})

        assert candidates == []

    def test_zero_area_obstruction_does_not_trigger(self) -> None:
        """Degenerate polygon with zero area should never trigger."""
        rule = make_rule(config={"threshold_ratio": 0.0, "min_duration_seconds": 0, "cooldown_seconds": 0})
        zero_area_detection = [(0.1, 0.1), (0.1, 0.1), (0.1, 0.1)]

        assert ObstructionRuleEngine.evaluate(10, [zero_area_detection], [rule], {}) == []

    def test_max_threshold_requires_more_than_full_area(self) -> None:
        """With threshold_ratio=1.0 the ratio must be *greater than* 1.0,
        which is impossible — so even a full-zone detection must not trigger."""
        rule = make_rule(config={"threshold_ratio": 1.0, "min_duration_seconds": 0, "cooldown_seconds": 0})
        full_roi_detection = square(0.0, 0.0, 1.0, 1.0)

        assert ObstructionRuleEngine.evaluate(10, [full_roi_detection], [rule], {}) == []

    def test_threshold_ratio_clamped_to_1_0(self) -> None:
        """Values > 1.0 are clamped, so a 2.0 threshold equals 1.0 — no trigger."""
        rule = make_rule(config={"threshold_ratio": 2.0, "min_duration_seconds": 0, "cooldown_seconds": 0})

        assert ObstructionRuleEngine.evaluate(10, [square(0.0, 0.0, 1.0, 1.0)], [rule], {}) == []

    def test_min_duration_seconds_must_elapse(self) -> None:
        """With min_duration_seconds > 0, the obstruction must be continuously
        present before an alert fires."""
        rule = make_rule(config={"threshold_ratio": 0.1, "min_duration_seconds": 5, "cooldown_seconds": 0})
        state: dict[int, float] = {}
        detection = square(0.0, 0.0, 0.6, 0.6)

        # First evaluation — registers the start time, no alert yet
        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], state) == []

        # Age by 3 seconds — still not enough
        age_active_condition(rule, state, 3)
        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], state) == []

        # Age by 6 total seconds — now it fires
        age_active_condition(rule, state, 3)
        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert len(candidates) == 1

    def test_picks_highest_ratio_among_multiple_detections(self) -> None:
        """When multiple detections overlap the ROI, the one with the highest
        occupied-area ratio should be reported."""
        rule = make_rule(config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        small = square(0.0, 0.0, 0.2, 0.2)   # 4% coverage
        big = square(0.0, 0.0, 0.5, 0.5)     # 25% coverage

        candidates = ObstructionRuleEngine.evaluate(10, [small, big], [rule], {})

        assert len(candidates) == 1
        assert candidates[0].evidence["metric_value"] == pytest.approx(0.25)

    def test_detection_outside_roi_ignored(self) -> None:
        """A detection entirely outside the ROI should not trigger."""
        rule = make_rule(config={"threshold_ratio": 0.01, "min_duration_seconds": 0, "cooldown_seconds": 0})
        outside = square(2.0, 2.0, 3.0, 3.0)

        assert ObstructionRuleEngine.evaluate(10, [outside], [rule], {}) == []

    def test_cooldown_suppresses_rapid_realert(self) -> None:
        """After an alert, a second alert within the cooldown window is suppressed."""
        rule = make_rule(config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 60})
        state: dict[int, float] = {}
        detection = square(0.0, 0.0, 0.5, 0.5)

        # First evaluation — should trigger
        c1 = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert len(c1) == 1

        # Second evaluation immediately — should be suppressed
        c2 = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert c2 == []

    def test_severity_low_when_ratio_just_above_threshold(self) -> None:
        rule = make_rule(config={"threshold_ratio": 0.3, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.55, 0.55)  # ~0.3025 ratio, just above

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        assert candidates[0].severity == AlertSeverity.low

    def test_severity_medium_when_ratio_1_5x_threshold(self) -> None:
        rule = make_rule(config={"threshold_ratio": 0.2, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.56, 0.56)  # ~0.3136 ratio ≥ 0.3

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        assert candidates[0].severity == AlertSeverity.medium

    def test_severity_high_when_ratio_2x_threshold(self) -> None:
        rule = make_rule(config={"threshold_ratio": 0.2, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.8, 0.8)  # 0.64 ratio ≥ 0.4

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        assert candidates[0].severity == AlertSeverity.high

    def test_severity_with_zero_threshold(self) -> None:
        """When threshold is 0, severity is based on raw ratio."""
        rule = make_rule(config={"threshold_ratio": 0.0, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.6, 0.6)  # 0.36 ratio

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        # 0.36 < 0.5 → medium
        assert candidates[0].severity == AlertSeverity.medium


# ===========================================================================
# ObstructionRuleEngine — Duration mode
# ===========================================================================


class TestDurationMode:
    """Tests for obstruction_duration rule type."""

    def test_triggers_after_minimum_duration(self) -> None:
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 5, "cooldown_seconds": 0},
        )
        cooldown_state: dict[int, float] = {}
        detection = square(0.0, 0.0, 1.0, 1.0)

        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], cooldown_state) == []
        age_active_condition(rule, cooldown_state, 6)
        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], cooldown_state)

        assert len(candidates) == 1
        assert candidates[0].rule_type == RuleType.obstruction_duration
        assert candidates[0].severity == AlertSeverity.low
        assert candidates[0].evidence["metric_value"] == pytest.approx(0.0)
        assert candidates[0].evidence["threshold"] == 0.3

    def test_does_not_trigger_before_minimum_duration(self) -> None:
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 5, "cooldown_seconds": 0},
        )
        cooldown_state: dict[int, float] = {}
        detection = square(0.0, 0.0, 1.0, 1.0)

        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], cooldown_state) == []
        age_active_condition(rule, cooldown_state, 4)

        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], cooldown_state) == []

    def test_threshold_fallback_key(self) -> None:
        """When `remaining_clear_width_threshold` is absent, falls back to `threshold`."""
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"threshold": 0.5, "min_stay_seconds": 0, "cooldown_seconds": 0},
        )
        detection = square(0.0, 0.0, 1.0, 1.0)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        assert candidates[0].evidence["threshold"] == 0.5

    def test_default_threshold_is_0_2(self) -> None:
        """When neither key is present, the default threshold is 0.2."""
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"min_stay_seconds": 0, "cooldown_seconds": 0},
        )
        detection = square(0.0, 0.0, 1.0, 1.0)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        assert candidates[0].evidence["threshold"] == pytest.approx(0.2)

    def test_clear_width_does_not_trigger_when_above_threshold(self) -> None:
        """A small detection that leaves enough clear width should not trigger."""
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 0, "cooldown_seconds": 0},
        )
        # Small obstruction near the edge — leaves > 0.3 clear width
        detection = square(0.0, 0.0, 0.2, 0.2)

        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], {}) == []

    def test_severity_medium_at_2x_threshold(self) -> None:
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 5, "cooldown_seconds": 0},
        )
        state: dict[int, float] = {}
        detection = square(0.0, 0.0, 1.0, 1.0)

        ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        age_active_condition(rule, state, 10)  # 2x threshold
        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert len(candidates) == 1
        assert candidates[0].severity == AlertSeverity.medium

    def test_severity_high_at_3x_threshold(self) -> None:
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 5, "cooldown_seconds": 0},
        )
        state: dict[int, float] = {}
        detection = square(0.0, 0.0, 1.0, 1.0)

        ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        age_active_condition(rule, state, 16)  # > 3x threshold
        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert len(candidates) == 1
        assert candidates[0].severity == AlertSeverity.high

    def test_severity_medium_when_zero_threshold(self) -> None:
        """With min_stay_seconds=0 (threshold 0), severity defaults to medium."""
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 0, "cooldown_seconds": 0},
        )
        detection = square(0.0, 0.0, 1.0, 1.0)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        assert candidates[0].severity == AlertSeverity.medium

    def test_direction_vertical(self) -> None:
        """The `direction` config key is read but geometry logic is delegated to ROIEngine."""
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 0, "cooldown_seconds": 0, "direction": "vertical"},
        )
        detection = square(0.0, 0.0, 1.0, 1.0)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1

    def test_active_state_cleared_when_obstruction_disappears(self) -> None:
        """When the detection is removed, the active-since state is cleared."""
        rule = make_rule(
            rule_type=RuleType.obstruction_duration,
            config={"remaining_clear_width_threshold": 0.3, "min_stay_seconds": 5, "cooldown_seconds": 0},
        )
        state: dict[int, float] = {}
        detection = square(0.0, 0.0, 1.0, 1.0)
        active_key = ObstructionRuleEngine._active_key(rule.rule_id, rule.roi_id)

        ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert active_key in state

        # Remove detection — should clear active state
        ObstructionRuleEngine.evaluate(10, [], [rule], state)
        assert active_key not in state


# ===========================================================================
# ObstructionRuleEngine — Forbidden-zone mode
# ===========================================================================


class TestForbiddenZoneMode:
    """Tests for forbidden_zone rule type."""

    def test_triggers_for_any_detection_in_zone(self) -> None:
        rule = make_rule(rule_type="forbidden_zone", config={"min_stay_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.25, 0.25, 0.35, 0.35)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})

        assert len(candidates) == 1
        assert candidates[0].rule_type == "forbidden_zone"
        assert candidates[0].severity == AlertSeverity.critical
        assert candidates[0].evidence["obstacle_polygon"] == detection

    def test_does_not_trigger_when_no_detection_overlaps(self) -> None:
        rule = make_rule(rule_type="forbidden_zone", config={"min_stay_seconds": 0, "cooldown_seconds": 0})
        outside = square(2.0, 2.0, 3.0, 3.0)

        assert ObstructionRuleEngine.evaluate(10, [outside], [rule], {}) == []

    def test_min_stay_seconds_enforced(self) -> None:
        """Detection in forbidden zone must persist for min_stay_seconds."""
        rule = make_rule(rule_type="forbidden_zone", config={"min_stay_seconds": 3, "cooldown_seconds": 0})
        state: dict[int, float] = {}
        detection = square(0.25, 0.25, 0.35, 0.35)

        # First call — registers start, no alert
        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], state) == []

        # Age 2 seconds — still not enough
        age_active_condition(rule, state, 2)
        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], state) == []

        # Age to 4 seconds — fires
        age_active_condition(rule, state, 2)
        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert len(candidates) == 1

    def test_evidence_fields(self) -> None:
        rule = make_rule(rule_type="forbidden_zone", config={"min_stay_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.1, 0.1, 0.2, 0.2)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        assert candidates[0].evidence["metric_value"] == 1.0
        assert candidates[0].evidence["threshold"] == 0.0

    def test_cooldown_suppresses_rapid_realert(self) -> None:
        rule = make_rule(rule_type="forbidden_zone", config={"min_stay_seconds": 0, "cooldown_seconds": 60})
        state: dict[int, float] = {}
        detection = square(0.1, 0.1, 0.2, 0.2)

        c1 = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert len(c1) == 1

        c2 = ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert c2 == []

    def test_active_state_cleared_when_detection_disappears(self) -> None:
        rule = make_rule(rule_type="forbidden_zone", config={"min_stay_seconds": 5, "cooldown_seconds": 0})
        state: dict[int, float] = {}
        detection = square(0.1, 0.1, 0.2, 0.2)
        active_key = ObstructionRuleEngine._active_key(rule.rule_id, rule.roi_id)

        ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        assert active_key in state

        ObstructionRuleEngine.evaluate(10, [], [rule], state)
        assert active_key not in state


# ===========================================================================
# ObstructionRuleEngine — General / edge cases
# ===========================================================================


class TestEngineGeneral:
    """Cross-cutting tests for ObstructionRuleEngine."""

    def test_empty_events_return_no_candidates_and_clear_active_state(self) -> None:
        rule = make_rule(config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        cooldown_state = {ObstructionRuleEngine._active_key(rule.rule_id, rule.roi_id): 123.0}

        assert ObstructionRuleEngine.evaluate(10, [], [rule], cooldown_state) == []
        assert ObstructionRuleEngine._active_key(rule.rule_id, rule.roi_id) not in cooldown_state

    def test_rules_for_different_camera_are_ignored(self) -> None:
        """A rule with camera_id != the evaluated camera_id is skipped."""
        rule = make_rule(camera_id=99, config={"threshold_ratio": 0.01, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.9, 0.9)

        # Evaluate for camera 10 — rule belongs to camera 99
        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], {}) == []

    def test_multiple_rules_evaluated_in_priority_order(self) -> None:
        """Rules are sorted by priority; lower number = higher priority."""
        r_low = make_rule(rule_id=1, priority=10, config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        r_high = make_rule(rule_id=2, priority=20, config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.5, 0.5)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [r_high, r_low], {})
        assert len(candidates) == 2
        # Lower priority number fires first
        assert candidates[0].rule_id == 1
        assert candidates[1].rule_id == 2

    def test_unknown_rule_type_produces_no_candidate(self) -> None:
        """A rule with an unrecognised type should silently return None."""
        rule = make_rule(rule_type="nonexistent_type", config={})
        detection = square(0.0, 0.0, 0.5, 0.5)

        assert ObstructionRuleEngine.evaluate(10, [detection], [rule], {}) == []

    def test_geometry_to_polygon_rect(self) -> None:
        geom: RectGeometry = {"type": "rect", "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}
        result = ObstructionRuleEngine._geometry_to_polygon(geom)
        assert len(result) == 4
        assert result[0] == pytest.approx((0.1, 0.2))
        assert result[1] == pytest.approx((0.4, 0.2))
        assert result[2] == pytest.approx((0.4, 0.6))
        assert result[3] == pytest.approx((0.1, 0.6))

    def test_geometry_to_polygon_polygon(self) -> None:
        geom: Geometry = {"type": "polygon", "points": [(0.1, 0.2), (0.3, 0.4), (0.5, 0.6)]}
        result = ObstructionRuleEngine._geometry_to_polygon(geom)
        assert result == [(0.1, 0.2), (0.3, 0.4), (0.5, 0.6)]

    def test_geometry_to_polygon_raw_points(self) -> None:
        pts: list[Point] = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
        result = ObstructionRuleEngine._geometry_to_polygon(pts)
        assert result == pts

    def test_rule_type_value_from_enum(self) -> None:
        assert ObstructionRuleEngine._rule_type_value(RuleType.obstruction_area) == "obstruction_area"

    def test_rule_type_value_from_string(self) -> None:
        assert ObstructionRuleEngine._rule_type_value("forbidden_zone") == "forbidden_zone"

    def test_float_config_returns_default_for_missing_key(self) -> None:
        assert ObstructionRuleEngine._float_config({}, "nonexistent", 4.2) == 4.2

    def test_float_config_casts_string_to_float(self) -> None:
        assert ObstructionRuleEngine._float_config({"key": "3.14"}, "key", 0.0) == pytest.approx(3.14)

    def test_float_config_returns_default_for_none_value(self) -> None:
        assert ObstructionRuleEngine._float_config({"key": None}, "key", 9.9) == 9.9

    def test_alert_key_deterministic(self) -> None:
        k1 = ObstructionRuleEngine._alert_key(1, 2)
        k2 = ObstructionRuleEngine._alert_key(1, 2)
        assert k1 == k2
        assert k1 > 0

    def test_active_key_is_negative_of_alert_key(self) -> None:
        assert ObstructionRuleEngine._active_key(1, 2) == -ObstructionRuleEngine._alert_key(1, 2)

    def test_evaluate_with_no_rules(self) -> None:
        detection = square(0.0, 0.0, 0.5, 0.5)
        assert ObstructionRuleEngine.evaluate(10, [detection], [], {}) == []

    def test_candidate_detected_at_is_aware_utc(self) -> None:
        rule = make_rule(config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.5, 0.5)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule], {})
        assert len(candidates) == 1
        dt = candidates[0].detected_at
        assert dt.tzinfo is not None

    def test_multiple_cameras_independent(self) -> None:
        """Rules for camera A should not interfere with camera B's evaluation."""
        rule_a = make_rule(rule_id=1, camera_id=10, config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        rule_b = make_rule(rule_id=2, camera_id=20, config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        detection = square(0.0, 0.0, 0.5, 0.5)

        candidates = ObstructionRuleEngine.evaluate(10, [detection], [rule_a, rule_b], {})
        assert len(candidates) == 1
        assert candidates[0].camera_id == 10

    def test_cooldown_state_records_alert_timestamp(self) -> None:
        """After triggering, the cooldown_state dict contains the alert timestamp."""
        rule = make_rule(config={"threshold_ratio": 0.1, "min_duration_seconds": 0, "cooldown_seconds": 0})
        state: dict[int, float] = {}
        detection = square(0.0, 0.0, 0.5, 0.5)

        ObstructionRuleEngine.evaluate(10, [detection], [rule], state)
        alert_key = ObstructionRuleEngine._alert_key(rule.rule_id, rule.roi_id)
        assert alert_key in state
        assert state[alert_key] > 0


# ===========================================================================
# CooldownTracker
# ===========================================================================


class TestCooldownTracker:
    """Tests for CooldownTracker (in-memory, time-based)."""

    def test_first_detection_always_passes(self) -> None:
        tracker = CooldownTracker()
        assert tracker.is_cooled_down(rule_id=1, roi_id=2, cooldown_seconds=60) is True

    def test_suppresses_second_detection_within_cooldown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        current_time = 1000.0
        monkeypatch.setattr(cooldown_module.time, "time", lambda: current_time)
        tracker = CooldownTracker()

        tracker.record_alert(rule_id=1, roi_id=2)
        current_time = 1030.0

        assert tracker.is_cooled_down(rule_id=1, roi_id=2, cooldown_seconds=60) is False

    def test_passes_after_cooldown_expires(self, monkeypatch: pytest.MonkeyPatch) -> None:
        current_time = 1000.0
        monkeypatch.setattr(cooldown_module.time, "time", lambda: current_time)
        tracker = CooldownTracker()

        tracker.record_alert(rule_id=1, roi_id=2)
        current_time = 1060.0

        assert tracker.is_cooled_down(rule_id=1, roi_id=2, cooldown_seconds=60) is True

    def test_independent_per_rule_and_roi(self, monkeypatch: pytest.MonkeyPatch) -> None:
        current_time = 1000.0
        monkeypatch.setattr(cooldown_module.time, "time", lambda: current_time)
        tracker = CooldownTracker()

        tracker.record_alert(rule_id=1, roi_id=2)
        current_time = 1010.0

        assert tracker.is_cooled_down(rule_id=1, roi_id=2, cooldown_seconds=60) is False
        assert tracker.is_cooled_down(rule_id=99, roi_id=2, cooldown_seconds=60) is True
        assert tracker.is_cooled_down(rule_id=1, roi_id=99, cooldown_seconds=60) is True

    def test_zero_cooldown_always_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        current_time = 1000.0
        monkeypatch.setattr(cooldown_module.time, "time", lambda: current_time)
        tracker = CooldownTracker()

        tracker.record_alert(rule_id=1, roi_id=2)
        current_time = 1000.1

        assert tracker.is_cooled_down(rule_id=1, roi_id=2, cooldown_seconds=0) is True

    def test_cleanup_removes_stale_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        current_time = 1000.0
        monkeypatch.setattr(cooldown_module.time, "time", lambda: current_time)
        tracker = CooldownTracker()

        tracker.record_alert(rule_id=1, roi_id=1)
        current_time = 1100.0
        tracker.record_alert(rule_id=2, roi_id=2)
        current_time = 2000.0

        tracker.cleanup(max_age_seconds=500)

        # (1,1) was recorded at t=1000, now at t=2000 → 1000s old > 500s → removed
        assert tracker.is_cooled_down(rule_id=1, roi_id=1, cooldown_seconds=99999) is True
        # (2,2) was recorded at t=1100, now at t=2000 → 900s old > 500s → removed
        assert tracker.is_cooled_down(rule_id=2, roi_id=2, cooldown_seconds=99999) is True

    def test_cleanup_keeps_recent_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        current_time = 1000.0
        monkeypatch.setattr(cooldown_module.time, "time", lambda: current_time)
        tracker = CooldownTracker()

        tracker.record_alert(rule_id=1, roi_id=1)
        current_time = 1050.0
        tracker.record_alert(rule_id=2, roi_id=2)
        current_time = 1100.0

        tracker.cleanup(max_age_seconds=80)

        # (1,1) at t=1000, now t=1100 → 100s old > 80s → removed
        assert tracker.is_cooled_down(rule_id=1, roi_id=1, cooldown_seconds=99999) is True
        # (2,2) at t=1050, now t=1100 → 50s old < 80s → kept
        assert tracker.is_cooled_down(rule_id=2, roi_id=2, cooldown_seconds=99999) is False

    def test_record_alert_updates_existing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        current_time = 1000.0
        monkeypatch.setattr(cooldown_module.time, "time", lambda: current_time)
        tracker = CooldownTracker()

        tracker.record_alert(rule_id=1, roi_id=1)
        current_time = 1050.0
        tracker.record_alert(rule_id=1, roi_id=1)
        current_time = 1060.0

        # Cooldown 60s from second record_alert at 1050 → expires at 1110
        assert tracker.is_cooled_down(rule_id=1, roi_id=1, cooldown_seconds=60) is False


# ===========================================================================
# AlertCandidate model
# ===========================================================================


class TestAlertCandidate:
    """Tests for AlertCandidate data model."""

    def test_creation_and_field_access(self) -> None:
        timestamp = datetime.now(timezone.utc)
        candidate = AlertCandidate(
            camera_id=10,
            roi_id=20,
            rule_id=30,
            rule_type=RuleType.obstruction_area,
            severity=AlertSeverity.high,
            evidence={"metric_value": 0.75, "threshold": 0.5},
            detected_at=timestamp,
        )

        assert candidate.camera_id == 10
        assert candidate.roi_id == 20
        assert candidate.rule_id == 30
        assert candidate.rule_type == RuleType.obstruction_area
        assert candidate.severity == AlertSeverity.high
        assert candidate.evidence == {"metric_value": 0.75, "threshold": 0.5}
        assert candidate.detected_at == timestamp

    def test_frozen_immutability(self) -> None:
        timestamp = datetime.now(timezone.utc)
        candidate = AlertCandidate(
            camera_id=1,
            roi_id=1,
            rule_id=1,
            rule_type=RuleType.obstruction_duration,
            severity=AlertSeverity.low,
            evidence={},
            detected_at=timestamp,
        )

        with pytest.raises(AttributeError):
            candidate.camera_id = 99  # type: ignore[misc]

    def test_rule_type_accepts_string(self) -> None:
        """rule_type is typed as RuleType | str — string values are valid."""
        candidate = AlertCandidate(
            camera_id=1,
            roi_id=1,
            rule_id=1,
            rule_type="forbidden_zone",
            severity=AlertSeverity.critical,
            evidence={},
            detected_at=datetime.now(timezone.utc),
        )
        assert candidate.rule_type == "forbidden_zone"

    def test_evidence_accepts_arbitrary_dict(self) -> None:
        evidence = {"zone_polygon": [(0, 0), (1, 0), (1, 1)], "nested": {"a": 1}}
        candidate = AlertCandidate(
            camera_id=1, roi_id=1, rule_id=1,
            rule_type=RuleType.obstruction_area,
            severity=AlertSeverity.medium,
            evidence=evidence,
            detected_at=datetime.now(timezone.utc),
        )
        assert candidate.evidence["nested"]["a"] == 1


# ===========================================================================
# RuleEvaluationResult model
# ===========================================================================


class TestRuleEvaluationResult:
    """Tests for RuleEvaluationResult data model."""

    def test_creation_fields(self) -> None:
        candidate = AlertCandidate(
            camera_id=1, roi_id=1, rule_id=1,
            rule_type=RuleType.obstruction_area,
            severity=AlertSeverity.low,
            evidence={},
            detected_at=datetime.now(timezone.utc),
        )
        result = RuleEvaluationResult(
            triggered=True,
            candidates=[candidate],
            roi_id=1,
            rule_id=1,
        )
        assert result.triggered is True
        assert len(result.candidates) == 1
        assert result.roi_id == 1
        assert result.rule_id == 1

    def test_not_triggered(self) -> None:
        result = RuleEvaluationResult(
            triggered=False,
            candidates=[],
            roi_id=2,
            rule_id=3,
        )
        assert result.triggered is False
        assert result.candidates == []

    def test_frozen_immutability(self) -> None:
        result = RuleEvaluationResult(triggered=False, candidates=[], roi_id=1, rule_id=1)
        with pytest.raises(AttributeError):
            result.triggered = True  # type: ignore[misc]


# ===========================================================================
# RuleConfig parsing (via _float_config)
# ===========================================================================


class TestRuleConfigParsing:
    """Verify _float_config works with TypedDict configs and raw dicts."""

    def test_typed_area_config(self) -> None:
        config: ObstructionAreaConfig = {"threshold_ratio": 0.25, "min_duration_seconds": 2.0, "cooldown_seconds": 5.0}
        assert ObstructionRuleEngine._float_config(config, "threshold_ratio", 0.0) == 0.25
        assert ObstructionRuleEngine._float_config(config, "min_duration_seconds", 0.0) == 2.0
        assert ObstructionRuleEngine._float_config(config, "cooldown_seconds", 0.0) == 5.0

    def test_typed_duration_config(self) -> None:
        config: ObstructionDurationConfig = {"min_stay_seconds": 3.0, "cooldown_seconds": 10.0}
        assert ObstructionRuleEngine._float_config(config, "min_stay_seconds", 0.0) == 3.0
        assert ObstructionRuleEngine._float_config(config, "cooldown_seconds", 0.0) == 10.0

    def test_typed_forbidden_config(self) -> None:
        config: ForbiddenZoneConfig = {"min_stay_seconds": 0.0, "cooldown_seconds": 15.0}
        assert ObstructionRuleEngine._float_config(config, "min_stay_seconds", 0.0) == 0.0
        assert ObstructionRuleEngine._float_config(config, "cooldown_seconds", 0.0) == 15.0

    def test_string_values_cast_to_float(self) -> None:
        raw = {"threshold_ratio": "0.25", "min_duration_seconds": "2", "cooldown_seconds": "5"}
        assert ObstructionRuleEngine._float_config(raw, "threshold_ratio", 0.0) == 0.25
        assert ObstructionRuleEngine._float_config(raw, "min_duration_seconds", 0.0) == 2.0
        assert ObstructionRuleEngine._float_config(raw, "cooldown_seconds", 0.0) == 5.0

    def test_missing_key_returns_default(self) -> None:
        assert ObstructionRuleEngine._float_config({}, "missing", 7.5) == 7.5

    def test_none_value_returns_default(self) -> None:
        assert ObstructionRuleEngine._float_config({"key": None}, "key", 9.9) == 9.9
