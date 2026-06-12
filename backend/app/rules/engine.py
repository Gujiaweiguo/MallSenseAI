"""Three-mode obstruction rule evaluation engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from ..models.entities import AlertSeverity, RuleType
from ..roi.engine import ROIEngine
from .config import RuleConfig
from .models import AlertCandidate

Point = tuple[float, float]


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

RuleTypeValue = RuleType | Literal["forbidden_zone"] | str

_STATE_KEY_FACTOR = 1_000_003


@dataclass(frozen=True)
class ActiveRule:
    """Runtime rule plus its normalized ROI geometry."""

    rule_id: int
    camera_id: int
    roi_id: int
    roi_geometry: Geometry | list[Point]
    rule_type: RuleTypeValue
    config: RuleConfig | dict[str, Any]
    priority: int


class ObstructionRuleEngine:
    """Stateless evaluator for obstruction duration, area, and forbidden-zone rules."""

    @classmethod
    def evaluate(
        cls,
        camera_id: int,
        detection_polygons: list[list[Point]],
        active_rules: list[ActiveRule],
        cooldown_state: dict[int, float],
    ) -> list[AlertCandidate]:
        """Evaluate detections against active rules and return alert candidates.

        ``cooldown_state`` is caller-owned mutable state. Positive keys store
        last-alert timestamps; negative keys store first-seen timestamps for a
        currently active rule/ROI condition. The engine has no internal state.
        """
        now = datetime.now(timezone.utc)
        now_ts = now.timestamp()
        candidates: list[AlertCandidate] = []

        for rule in sorted(active_rules, key=lambda item: item.priority):
            if rule.camera_id != camera_id:
                continue

            roi_polygon = cls._geometry_to_polygon(rule.roi_geometry)
            rule_type = cls._rule_type_value(rule.rule_type)
            candidate = cls._evaluate_rule(rule, rule_type, roi_polygon, detection_polygons, cooldown_state, now, now_ts)
            if candidate is not None:
                candidates.append(candidate)

        return candidates

    @classmethod
    def _evaluate_rule(
        cls,
        rule: ActiveRule,
        rule_type: str,
        roi_polygon: list[Point],
        detection_polygons: list[list[Point]],
        cooldown_state: dict[int, float],
        now: datetime,
        now_ts: float,
    ) -> AlertCandidate | None:
        if rule_type == RuleType.obstruction_duration.value:
            return cls._evaluate_obstruction_duration(rule, roi_polygon, detection_polygons, cooldown_state, now, now_ts)
        if rule_type == RuleType.obstruction_area.value:
            return cls._evaluate_obstruction_area(rule, roi_polygon, detection_polygons, cooldown_state, now, now_ts)
        if rule_type == "forbidden_zone":
            return cls._evaluate_forbidden_zone(rule, roi_polygon, detection_polygons, cooldown_state, now, now_ts)
        return None

    @classmethod
    def _evaluate_obstruction_duration(
        cls,
        rule: ActiveRule,
        roi_polygon: list[Point],
        detection_polygons: list[list[Point]],
        cooldown_state: dict[int, float],
        now: datetime,
        now_ts: float,
    ) -> AlertCandidate | None:
        threshold = cls._float_config(rule.config, "remaining_clear_width_threshold", cls._float_config(rule.config, "threshold", 0.2))
        min_stay_seconds = cls._float_config(rule.config, "min_stay_seconds", 0.0)
        cooldown_seconds = cls._float_config(rule.config, "cooldown_seconds", 0.0)
        direction = str(rule.config.get("direction") or "horizontal")

        best_polygon: list[Point] | None = None
        best_width: float | None = None
        for detection_polygon in detection_polygons:
            if ROIEngine.polygon_intersection(roi_polygon, detection_polygon) is None:
                continue
            clear_width = ROIEngine.remaining_clear_width(roi_polygon, detection_polygon, direction)
            if clear_width < threshold and (best_width is None or clear_width < best_width):
                best_width = clear_width
                best_polygon = detection_polygon

        if best_polygon is None or best_width is None:
            cls._clear_active_since(cooldown_state, rule.rule_id, rule.roi_id)
            return None

        active_seconds = cls._active_seconds(cooldown_state, rule.rule_id, rule.roi_id, now_ts)
        if active_seconds < min_stay_seconds or not cls._is_cooled_down(cooldown_state, rule.rule_id, rule.roi_id, cooldown_seconds, now_ts):
            return None

        cls._record_alert(cooldown_state, rule.rule_id, rule.roi_id, now_ts)
        return cls._candidate(
            rule=rule,
            rule_type=RuleType.obstruction_duration,
            severity=cls._duration_severity(active_seconds, min_stay_seconds),
            roi_polygon=roi_polygon,
            obstacle_polygon=best_polygon,
            metric_value=best_width,
            threshold=threshold,
            detected_at=now,
        )

    @classmethod
    def _evaluate_obstruction_area(
        cls,
        rule: ActiveRule,
        roi_polygon: list[Point],
        detection_polygons: list[list[Point]],
        cooldown_state: dict[int, float],
        now: datetime,
        now_ts: float,
    ) -> AlertCandidate | None:
        threshold = max(0.0, min(1.0, cls._float_config(rule.config, "threshold_ratio", 0.0)))
        min_duration_seconds = cls._float_config(rule.config, "min_duration_seconds", 0.0)
        cooldown_seconds = cls._float_config(rule.config, "cooldown_seconds", 0.0)

        best_polygon: list[Point] | None = None
        best_ratio = 0.0
        for detection_polygon in detection_polygons:
            ratio = ROIEngine.occupied_area_ratio(roi_polygon, detection_polygon)
            if ratio > best_ratio:
                best_ratio = ratio
                best_polygon = detection_polygon

        if best_polygon is None or best_ratio <= threshold:
            cls._clear_active_since(cooldown_state, rule.rule_id, rule.roi_id)
            return None

        active_seconds = cls._active_seconds(cooldown_state, rule.rule_id, rule.roi_id, now_ts)
        if active_seconds < min_duration_seconds or not cls._is_cooled_down(cooldown_state, rule.rule_id, rule.roi_id, cooldown_seconds, now_ts):
            return None

        cls._record_alert(cooldown_state, rule.rule_id, rule.roi_id, now_ts)
        return cls._candidate(
            rule=rule,
            rule_type=RuleType.obstruction_area,
            severity=cls._ratio_severity(best_ratio, threshold),
            roi_polygon=roi_polygon,
            obstacle_polygon=best_polygon,
            metric_value=best_ratio,
            threshold=threshold,
            detected_at=now,
        )

    @classmethod
    def _evaluate_forbidden_zone(
        cls,
        rule: ActiveRule,
        roi_polygon: list[Point],
        detection_polygons: list[list[Point]],
        cooldown_state: dict[int, float],
        now: datetime,
        now_ts: float,
    ) -> AlertCandidate | None:
        min_stay_seconds = cls._float_config(rule.config, "min_stay_seconds", 0.0)
        cooldown_seconds = cls._float_config(rule.config, "cooldown_seconds", 0.0)

        entered_polygon = next(
            (polygon for polygon in detection_polygons if ROIEngine.is_in_forbidden_zone(polygon, roi_polygon)),
            None,
        )
        if entered_polygon is None:
            cls._clear_active_since(cooldown_state, rule.rule_id, rule.roi_id)
            return None

        active_seconds = cls._active_seconds(cooldown_state, rule.rule_id, rule.roi_id, now_ts)
        if active_seconds < min_stay_seconds or not cls._is_cooled_down(cooldown_state, rule.rule_id, rule.roi_id, cooldown_seconds, now_ts):
            return None

        cls._record_alert(cooldown_state, rule.rule_id, rule.roi_id, now_ts)
        return cls._candidate(
            rule=rule,
            rule_type="forbidden_zone",
            severity=AlertSeverity.critical,
            roi_polygon=roi_polygon,
            obstacle_polygon=entered_polygon,
            metric_value=1.0,
            threshold=0.0,
            detected_at=now,
        )

    @staticmethod
    def _candidate(
        rule: ActiveRule,
        rule_type: RuleType | str,
        severity: AlertSeverity,
        roi_polygon: list[Point],
        obstacle_polygon: list[Point],
        metric_value: float,
        threshold: float,
        detected_at: datetime,
    ) -> AlertCandidate:
        return AlertCandidate(
            camera_id=rule.camera_id,
            roi_id=rule.roi_id,
            rule_id=rule.rule_id,
            rule_type=rule_type,
            severity=severity,
            evidence={
                "zone_polygon": roi_polygon,
                "obstacle_polygon": obstacle_polygon,
                "metric_value": metric_value,
                "threshold": threshold,
            },
            detected_at=detected_at,
        )

    @staticmethod
    def _geometry_to_polygon(geometry: Geometry | list[Point]) -> list[Point]:
        if isinstance(geometry, list):
            return [(float(x), float(y)) for x, y in geometry]
        if geometry["type"] == "polygon":
            return [(float(x), float(y)) for x, y in geometry["points"]]
        x = float(geometry["x"])
        y = float(geometry["y"])
        width = float(geometry["width"])
        height = float(geometry["height"])
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]

    @staticmethod
    def _rule_type_value(rule_type: RuleTypeValue) -> str:
        value = getattr(rule_type, "value", rule_type)
        return str(value)

    @staticmethod
    def _float_config(config: RuleConfig | dict[str, Any], key: str, default: float) -> float:
        value = config.get(key, default)
        if value is None:
            return default
        return float(value)

    @staticmethod
    def _alert_key(rule_id: int, roi_id: int) -> int:
        return (rule_id * _STATE_KEY_FACTOR) + roi_id

    @classmethod
    def _active_key(cls, rule_id: int, roi_id: int) -> int:
        return -cls._alert_key(rule_id, roi_id)

    @classmethod
    def _active_seconds(cls, cooldown_state: dict[int, float], rule_id: int, roi_id: int, now_ts: float) -> float:
        key = cls._active_key(rule_id, roi_id)
        first_seen_at = cooldown_state.setdefault(key, now_ts)
        return now_ts - first_seen_at

    @classmethod
    def _clear_active_since(cls, cooldown_state: dict[int, float], rule_id: int, roi_id: int) -> None:
        cooldown_state.pop(cls._active_key(rule_id, roi_id), None)

    @classmethod
    def _is_cooled_down(
        cls,
        cooldown_state: dict[int, float],
        rule_id: int,
        roi_id: int,
        cooldown_seconds: float,
        now_ts: float,
    ) -> bool:
        last_alert_at = cooldown_state.get(cls._alert_key(rule_id, roi_id))
        return last_alert_at is None or (now_ts - last_alert_at) >= cooldown_seconds

    @classmethod
    def _record_alert(cls, cooldown_state: dict[int, float], rule_id: int, roi_id: int, now_ts: float) -> None:
        cooldown_state[cls._alert_key(rule_id, roi_id)] = now_ts

    @staticmethod
    def _duration_severity(active_seconds: float, threshold_seconds: float) -> AlertSeverity:
        if threshold_seconds <= 0:
            return AlertSeverity.medium
        if active_seconds >= threshold_seconds * 3:
            return AlertSeverity.high
        if active_seconds >= threshold_seconds * 2:
            return AlertSeverity.medium
        return AlertSeverity.low

    @staticmethod
    def _ratio_severity(ratio: float, threshold: float) -> AlertSeverity:
        if threshold <= 0:
            return AlertSeverity.high if ratio >= 0.5 else AlertSeverity.medium
        if ratio >= min(1.0, threshold * 2):
            return AlertSeverity.high
        if ratio >= min(1.0, threshold * 1.5):
            return AlertSeverity.medium
        return AlertSeverity.low
