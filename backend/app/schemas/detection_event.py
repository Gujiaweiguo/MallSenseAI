from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.app.models import DetectorType


class DetectionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    roi_id: int | None
    detector_type: DetectorType
    confidence: float | None
    evidence_path: str | None
    event_metadata: dict[str, Any]
    detected_at: datetime
