from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import NotificationChannelType


# ---------------------------------------------------------------------------
# Notification Channel
# ---------------------------------------------------------------------------


class NotificationChannelCreate(BaseModel):
    channel_type: NotificationChannelType
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    config: dict | None = None
    enabled: bool | None = None


class NotificationChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    channel_type: NotificationChannelType
    config: dict
    enabled: bool


# ---------------------------------------------------------------------------
# Notification Group
# ---------------------------------------------------------------------------


class NotificationGroupCreate(BaseModel):
    name: str = Field(max_length=128)
    severities: list[str] = Field(default_factory=list)
    enabled: bool = True


class NotificationGroupUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    severities: list[str] | None = None
    enabled: bool | None = None


class NotificationGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channels: dict
    enabled: bool
    created_at: datetime
    updated_at: datetime
    notification_channels: list[NotificationChannelResponse] = []
