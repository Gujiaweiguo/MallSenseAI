"""ROI geometry package — normalized [0, 1] coordinate space.

Provides:
- :mod:`types` — SceneType, ZonePurpose, ROIMetadata
- :mod:`validation` — polygon and rectangle validation
- :mod:`engine` — ROIEngine with core + obstruction geometry ops
- :mod:`importer` — legacy safe_zones.json conversion
"""

from __future__ import annotations

from backend.app.roi.engine import ROIEngine
from backend.app.roi.importer import ImportedROI, import_legacy_safe_zones
from backend.app.roi.types import ROIMetadata, SceneType, ZonePurpose
from backend.app.roi.validation import ValidationResult, validate_polygon, validate_rect

__all__ = [
    "ROIEngine",
    "ImportedROI",
    "import_legacy_safe_zones",
    "ROIMetadata",
    "SceneType",
    "ZonePurpose",
    "ValidationResult",
    "validate_polygon",
    "validate_rect",
]
