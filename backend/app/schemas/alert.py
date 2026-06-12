from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from backend.app.models import AlertSeverity, AlertStatus, RuleType


class AlertUpdate(BaseModel):
    status: AlertStatus

    @field_validator("status")
    @classmethod
    def status_must_be_terminal_action(cls, value: AlertStatus) -> AlertStatus:
        if value not in {AlertStatus.confirmed, AlertStatus.false_positive, AlertStatus.resolved}:
            raise ValueError("status must be confirmed, false_positive, or resolved")
        return value


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    roi_id: int | None
    rule_id: int | None
    alert_type: RuleType
    severity: AlertSeverity
    status: AlertStatus
    evidence_image_path: str | None
    detected_at: datetime
    resolved_at: datetime | None
    event_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
