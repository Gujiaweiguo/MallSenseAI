from __future__ import annotations

from pathlib import Path

ASSET_ROOT = Path("data/assets")
CAMERA_ASSET_ROOT = ASSET_ROOT / "cameras"
ALERT_ASSET_ROOT = ASSET_ROOT / "alerts"
ROI_ASSET_ROOT = ASSET_ROOT / "rois"
LEGACY_ALARM_IMAGES_ROOT = Path("alarm_images")

BASELINE_IMAGE_TEMPLATE = "data/assets/cameras/{camera_id}/baseline.jpg"
EVIDENCE_IMAGE_TEMPLATE = "data/assets/alerts/{alert_id}/evidence.jpg"
ROI_SNAPSHOT_TEMPLATE = "data/assets/rois/{roi_id}/preview.jpg"


def baseline_image_path(camera_id: int) -> Path:
    return Path(BASELINE_IMAGE_TEMPLATE.format(camera_id=camera_id))


def evidence_image_path(alert_id: int) -> Path:
    return Path(EVIDENCE_IMAGE_TEMPLATE.format(alert_id=alert_id))


def roi_snapshot_path(roi_id: int) -> Path:
    return Path(ROI_SNAPSHOT_TEMPLATE.format(roi_id=roi_id))


def resolve_legacy_asset_path(legacy_path: str | Path, *, camera_id: int | None = None, alert_id: int | None = None, roi_id: int | None = None) -> Path:
    """Map a known legacy asset path to its canonical platform destination."""
    path = Path(legacy_path)
    name = path.name.lower()
    if name == "base_image.jpg":
        if camera_id is None:
            raise ValueError("camera_id is required for legacy baseline images")
        return baseline_image_path(camera_id)
    if name == "safe_zones.json" or "roi" in name:
        if roi_id is None:
            raise ValueError("roi_id is required for legacy ROI assets")
        return roi_snapshot_path(roi_id)
    if name in {"detection_result.jpg", "alarm_last.jpg"} or "evidence" in name or "alarm" in name:
        if alert_id is None:
            raise ValueError("alert_id is required for legacy evidence images")
        return evidence_image_path(alert_id)
    raise ValueError(f"No canonical asset mapping for legacy path: {path}")
