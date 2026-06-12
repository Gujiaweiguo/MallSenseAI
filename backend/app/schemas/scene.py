from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SceneCreate(BaseModel):
    camera_id: int
    name: str = Field(max_length=128)


class SceneUpdate(BaseModel):
    camera_id: int | None = None
    name: str | None = Field(default=None, max_length=128)


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    name: str
    baseline_image_path: str | None
    created_at: datetime
    updated_at: datetime
