from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from backend.app.models import UserRole


class UserCreate(BaseModel):
    username: str = Field(max_length=128)
    password: str = Field(min_length=1)
    display_name: str = Field(max_length=128)
    role: UserRole = UserRole.viewer
    enabled: bool = True


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, min_length=1)
    display_name: str | None = Field(default=None, max_length=128)
    role: UserRole | None = None
    enabled: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: UserRole
    enabled: bool
    created_at: datetime
    updated_at: datetime
