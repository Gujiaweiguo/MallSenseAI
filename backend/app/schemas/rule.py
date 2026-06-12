from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import RuleType


class RuleCreate(BaseModel):
    camera_id: int
    roi_id: int | None = None
    rule_type: RuleType
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    priority: int = 100


class RuleUpdate(BaseModel):
    camera_id: int | None = None
    roi_id: int | None = None
    rule_type: RuleType | None = None
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    priority: int | None = None


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    roi_id: int | None
    rule_type: RuleType
    config: dict[str, Any]
    enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime
