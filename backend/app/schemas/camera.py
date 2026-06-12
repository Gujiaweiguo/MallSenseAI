from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import CameraStatus


class CameraCreate(BaseModel):
    name: str = Field(max_length=128)
    location: str = Field(max_length=255)
    ip: str = Field(max_length=64)
    port: int = 80
    username: str = Field(max_length=128)
    password: str = Field(min_length=1)
    status: CameraStatus = CameraStatus.active


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    location: str | None = Field(default=None, max_length=255)
    ip: str | None = Field(default=None, max_length=64)
    port: int | None = None
    username: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, min_length=1)
    status: CameraStatus | None = None


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    ip: str
    port: int
    status: CameraStatus
    created_at: datetime
    updated_at: datetime
