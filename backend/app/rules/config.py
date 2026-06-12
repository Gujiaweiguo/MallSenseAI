"""Configuration schemas for obstruction rules."""

from __future__ import annotations

from typing import TypedDict, Union  # noqa: UP007 — Python 3.10 compat


class ObstructionDurationConfig(TypedDict):
    """Config for duration-based passage obstruction."""

    min_stay_seconds: float
    cooldown_seconds: float


class ObstructionAreaConfig(TypedDict):
    """Config for area-ratio obstruction."""

    threshold_ratio: float
    min_duration_seconds: float
    cooldown_seconds: float


class ForbiddenZoneConfig(TypedDict):
    """Config for forbidden-zone intrusion."""

    min_stay_seconds: float
    cooldown_seconds: float



class DebrisConfig(TypedDict):
    """Config for debris / litter detection in floor zones.

    Attributes:
        debris_classes: YOLO class names to treat as debris.
        min_confidence: Minimum detection confidence to trigger.
        min_area_ratio: Minimum detection-area / ROI-area ratio.
        duration_seconds: How long debris must persist before alerting.
        cooldown_seconds: Minimum interval between repeated alerts.
    """

    debris_classes: list[str]
    min_confidence: float
    min_area_ratio: float
    duration_seconds: float
    cooldown_seconds: float


class FireSmokeConfig(TypedDict):
    """Config for fire/smoke detection."""

    confidence_threshold: float
    min_area_ratio: float
    cooldown_seconds: float


RuleConfig = Union[
    ObstructionDurationConfig,
    ObstructionAreaConfig,
    ForbiddenZoneConfig,
    DebrisConfig,
    FireSmokeConfig,
]
