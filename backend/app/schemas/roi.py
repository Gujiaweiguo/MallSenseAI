from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import ZoneType


class ROICreate(BaseModel):
    scene_id: int
    name: str = Field(max_length=128)
    zone_type: ZoneType
    geometry: dict[str, Any]
    normalized_coords: bool = True
    color: str | None = Field(default=None, max_length=32)


class ROIUpdate(BaseModel):
    scene_id: int | None = None
    name: str | None = Field(default=None, max_length=128)
    zone_type: ZoneType | None = None
    geometry: dict[str, Any] | None = None
    normalized_coords: bool | None = None
    color: str | None = Field(default=None, max_length=32)


class ROIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scene_id: int
    name: str
    zone_type: ZoneType
    geometry: dict[str, Any]
    normalized_coords: bool
    color: str | None
    created_at: datetime
    updated_at: datetime
