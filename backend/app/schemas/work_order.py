from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from backend.app.models import WorkOrderStatus


class WorkOrderCreate(BaseModel):
    alert_id: int
    assigned_to: int | None = None
    status: WorkOrderStatus = WorkOrderStatus.open
    notes: str | None = None


class WorkOrderUpdate(BaseModel):
    alert_id: int | None = None
    assigned_to: int | None = None
    status: WorkOrderStatus | None = None
    notes: str | None = None


class WorkOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int
    assigned_to: int | None
    status: WorkOrderStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
