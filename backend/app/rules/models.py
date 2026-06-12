"""Rule-engine internal models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..models.entities import AlertSeverity, RuleType


@dataclass(frozen=True)
class AlertCandidate:
    """A caller-persistable alert candidate produced by rule evaluation."""

    camera_id: int
    roi_id: int
    rule_id: int
    rule_type: RuleType | str
    severity: AlertSeverity
    evidence: dict[str, Any]
    detected_at: datetime


@dataclass(frozen=True)
class RuleEvaluationResult:
    """Result for one rule/ROI evaluation."""

    triggered: bool
    candidates: list[AlertCandidate]
    roi_id: int
    rule_id: int
