from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import RuleType


class RuleDefinitionCreate(BaseModel):
    name: str = Field(max_length=128)
    rule_type: RuleType
    config: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


class RuleDefinitionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    config: dict[str, Any] | None = None
    description: str | None = None


class RuleDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rule_type: RuleType
    config: dict[str, Any]
    description: str | None
    created_at: datetime
    updated_at: datetime
