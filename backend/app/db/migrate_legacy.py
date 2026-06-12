from __future__ import annotations

import ast
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.password import hash_password
from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal, engine
from backend.app.models import (
    Base,
    Camera,
    CameraStatus,
    NotificationChannel,
    NotificationChannelType,
    NotificationGroup,
    ROI,
    Rule,
    RuleType,
    Scene,
    ZoneType,
)
from shared.asset_paths import baseline_image_path, resolve_legacy_asset_path
from shared.coordinate_standard import LEGACY_RUNTIME_HEIGHT, LEGACY_RUNTIME_WIDTH, legacy_1000x750_to_normalized

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CAMERA_CONFIG_PATH = PROJECT_ROOT / "camera_configs.json"
LEGACY_CONFIG_PATH = PROJECT_ROOT / "config.py"
ALARM_IMAGES_ROOT = PROJECT_ROOT / "alarm_images"
KNOWN_DUPLICATE_LOCATION = "4层西山4014铺旁通道"
KNOWN_DUPLICATE_IPS = {"10.25.4.125", "10.25.4.128"}
NOTIFICATION_GROUP_NAME = "Legacy WeCom Default"
WECOM_SECRET_REF = "LEGACY_WECOM_WEBHOOK_URL"


@dataclass
class MigrationReport:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    conflicts: int = 0
    details: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.details.append(message)


@dataclass
class FullMigrationReport:
    cameras: MigrationReport
    scenes: MigrationReport
    rois: MigrationReport
    rules: MigrationReport
    dry_run: bool


@dataclass(frozen=True)
class _CameraRow:
    id: int | None
    name: str
    location: str
    ip: str
    port: int
    username: str


def _load_legacy_cameras() -> list[dict[str, Any]]:
    if not CAMERA_CONFIG_PATH.exists():
        return []
    with CAMERA_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, list) else []


def _location_counts(cameras: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in cameras:
        location = str(row.get("location") or "").strip()
        if location:
            counts[location] = counts.get(location, 0) + 1
    return counts


def _coerce_port(value: Any) -> int:
    try:
        return int(value or 80)
    except (TypeError, ValueError):
        return 80


def _camera_name(row: dict[str, Any], index: int, counts: dict[str, int]) -> str:
    location = str(row.get("location") or "").strip() or f"Legacy camera {index + 1}"
    if counts.get(location, 0) > 1:
        return f"{location} ({row.get('ip')})"
    return location


def _legacy_config_dict(name: str) -> tuple[dict[str, Any], list[str]]:
    if not LEGACY_CONFIG_PATH.exists():
        return {}, []
    tree = ast.parse(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            if not isinstance(node.value, ast.Dict):
                return {}, []
            result: dict[str, Any] = {}
            duplicate_keys: list[str] = []
            seen: set[str] = set()
            for key_node, value_node in zip(node.value.keys, node.value.values, strict=False):
                if key_node is None:
                    continue
                try:
                    key = ast.literal_eval(key_node)
                except (ValueError, SyntaxError):
                    continue
                if not isinstance(key, str):
                    continue
                if key in seen:
                    duplicate_keys.append(key)
                seen.add(key)
                try:
                    result[key] = ast.literal_eval(value_node)
                except (ValueError, SyntaxError):
                    continue
            return result, duplicate_keys
    return {}, []


def _ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)


def _camera_rows_for_migration(db: Session, dry_run: bool) -> tuple[list[_CameraRow], MigrationReport]:
    report = MigrationReport()
    legacy = _load_legacy_cameras()
    counts = _location_counts(legacy)
    rows: list[_CameraRow] = []
    for index, row in enumerate(legacy):
        ip = str(row.get("ip") or "").strip()
        if not ip:
            report.skipped += 1
            report.add(f"invalid_camera_missing_ip index={index}")
            continue
        port = _coerce_port(row.get("port"))
        existing = db.scalar(select(Camera).where(Camera.ip == ip, Camera.port == port))
        rows.append(
            _CameraRow(
                id=existing.id if existing is not None else (None if not dry_run else -(index + 1)),
                name=_camera_name(row, index, counts),
                location=str(row.get("location") or "").strip(),
                ip=ip,
                port=port,
                username=str(row.get("username") or "").strip(),
            )
        )
    return rows, report


def _copy_if_changed(source: Path, destination: Path, dry_run: bool) -> str:
    if not source.exists():
        return "missing"
    if destination.exists() and _sha256(source) == _sha256(destination):
        return "unchanged"
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return "copied"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_scene_name(camera: _CameraRow | Camera) -> str:
    return f"{camera.name} default scene"


def _roi_source_matches(roi: ROI, source_path: str, source_index: int) -> bool:
    source = roi.geometry.get("source") if isinstance(roi.geometry, dict) else None
    return isinstance(source, dict) and source.get("path") == source_path and source.get("index") == source_index


def _is_degenerate_polygon(points: list[tuple[float, float]]) -> bool:
    if not points or all(x == 0 and y == 0 for x, y in points):
        return True
    return len(set(points)) < 3


def migrate_cameras(dry_run: bool = False) -> MigrationReport:
    report = MigrationReport()
    legacy = _load_legacy_cameras()
    counts = _location_counts(legacy)
    if not legacy:
        report.conflicts += 1
        report.add(f"camera_configs_missing_or_empty path={CAMERA_CONFIG_PATH}")
        return report
    _ensure_schema()
    with SessionLocal() as db:
        for index, row in enumerate(legacy):
            ip = str(row.get("ip") or "").strip()
            if not ip:
                report.skipped += 1
                report.add(f"invalid_camera_missing_ip index={index}")
                continue
            port = _coerce_port(row.get("port"))
            location = str(row.get("location") or "").strip()
            username = str(row.get("username") or "").strip()
            password = row.get("password")
            name = _camera_name(row, index, counts)
            if counts.get(location, 0) > 1:
                report.conflicts += 1
                report.add(f"duplicate_location location={location!r} ip={ip} port={port}")
            if location == KNOWN_DUPLICATE_LOCATION and ip in KNOWN_DUPLICATE_IPS:
                report.add(f"known_duplicate_location_collision location={location!r} ip={ip}")
            existing = db.scalar(select(Camera).where(Camera.ip == ip, Camera.port == port))
            if existing is None:
                if not isinstance(password, str) or not password:
                    report.skipped += 1
                    report.add(f"invalid_camera_missing_password ip={ip} port={port}")
                    continue
                try:
                    password_hash = "<dry-run>" if dry_run else hash_password(password)
                except Exception as exc:  # pragma: no cover - passlib backend failure only
                    report.skipped += 1
                    report.add(f"password_hash_failed ip={ip} port={port} error={exc.__class__.__name__}")
                    continue
                report.inserted += 1
                report.add(f"camera_insert ip={ip} port={port} location={location!r} password_present=true")
                if not dry_run:
                    db.add(Camera(name=name, location=location, ip=ip, port=port, username=username, password_hash=password_hash, status=CameraStatus.active))
                continue
            changes: dict[str, Any] = {}
            for attr, value in {"name": name, "location": location, "username": username, "status": CameraStatus.active}.items():
                if getattr(existing, attr) != value:
                    changes[attr] = value
            if changes:
                report.updated += 1
                report.add(f"camera_update ip={ip} port={port} fields={sorted(changes)}")
                if not dry_run:
                    for attr, value in changes.items():
                        setattr(existing, attr, value)
            else:
                report.skipped += 1
                report.add(f"camera_exists_unchanged ip={ip} port={port}")
        if not dry_run:
            db.commit()
    return report


def migrate_scenes_and_baselines(dry_run: bool = False) -> MigrationReport:
    report = MigrationReport()
    legacy = _load_legacy_cameras()
    counts = _location_counts(legacy)
    _ensure_schema()
    with SessionLocal() as db:
        camera_rows, invalid_report = _camera_rows_for_migration(db, dry_run)
        report.skipped += invalid_report.skipped
        report.details.extend(invalid_report.details)
        for camera in camera_rows:
            if camera.id is None:
                report.skipped += 1
                report.add(f"scene_skipped_camera_not_migrated ip={camera.ip} port={camera.port}")
                continue
            if counts.get(camera.location, 0) > 1:
                report.conflicts += 1
                report.add(f"location_collision baseline location={camera.location!r} camera_ip={camera.ip}")
            scene_name = _default_scene_name(camera)
            source = ALARM_IMAGES_ROOT / camera.location / "base_image.jpg"
            target = PROJECT_ROOT / resolve_legacy_asset_path(source, camera_id=abs(camera.id))
            copy_status = _copy_if_changed(source, target, dry_run)
            baseline_value = str(baseline_image_path(abs(camera.id))) if copy_status != "missing" else None
            if copy_status == "missing":
                report.add(f"missing_baseline location={camera.location!r} path={source.relative_to(PROJECT_ROOT)}")
            scene = None if camera.id < 0 else db.scalar(select(Scene).where(Scene.camera_id == camera.id, Scene.name == scene_name))
            if scene is None:
                report.inserted += 1
                report.add(f"scene_insert camera_ip={camera.ip} name={scene_name!r} baseline={baseline_value!r} copy_status={copy_status}")
                if not dry_run:
                    db.add(Scene(camera_id=camera.id, name=scene_name, baseline_image_path=baseline_value))
            elif scene.baseline_image_path != baseline_value and baseline_value is not None:
                report.updated += 1
                report.add(f"scene_update_baseline camera_ip={camera.ip} name={scene_name!r} baseline={baseline_value!r} copy_status={copy_status}")
                if not dry_run:
                    scene.baseline_image_path = baseline_value
            else:
                report.skipped += 1
                report.add(f"scene_exists_unchanged camera_ip={camera.ip} name={scene_name!r}")
        if not dry_run:
            db.commit()
    return report


def migrate_rois(dry_run: bool = False) -> MigrationReport:
    report = MigrationReport()
    legacy = _load_legacy_cameras()
    counts = _location_counts(legacy)
    _ensure_schema()
    with SessionLocal() as db:
        camera_rows, invalid_report = _camera_rows_for_migration(db, dry_run)
        report.skipped += invalid_report.skipped
        report.details.extend(invalid_report.details)
        for camera in camera_rows:
            if camera.id is None:
                report.skipped += 1
                report.add(f"roi_skipped_camera_not_migrated ip={camera.ip} port={camera.port}")
                continue
            if counts.get(camera.location, 0) > 1:
                report.conflicts += 1
                report.add(f"location_collision roi location={camera.location!r} camera_ip={camera.ip}")
            scene_name = _default_scene_name(camera)
            scene = None if camera.id < 0 else db.scalar(select(Scene).where(Scene.camera_id == camera.id, Scene.name == scene_name))
            scene_id = camera.id if dry_run and camera.id < 0 else (scene.id if scene is not None else None)
            if scene_id is None:
                report.skipped += 1
                report.add(f"roi_skipped_scene_missing camera_ip={camera.ip} scene={scene_name!r}")
                continue
            source = ALARM_IMAGES_ROOT / camera.location / "safe_zones.json"
            source_rel = str(source.relative_to(PROJECT_ROOT))
            if not source.exists():
                report.skipped += 1
                report.add(f"missing_safe_zones location={camera.location!r} path={source_rel}")
                continue
            try:
                zones = json.loads(source.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                report.conflicts += 1
                report.add(f"corrupted_safe_zones path={source_rel} error={exc.msg}")
                continue
            if not isinstance(zones, list):
                report.conflicts += 1
                report.add(f"corrupted_safe_zones path={source_rel} error=expected_list")
                continue
            for zone_index, zone in enumerate(zones):
                zone_type = zone.get("type") if isinstance(zone, dict) else None
                data = zone.get("data") if isinstance(zone, dict) else None
                try:
                    if zone_type == "polygon":
                        if not isinstance(data, list):
                            raise TypeError("polygon data must be a list")
                        points = [(float(point[0]), float(point[1])) for point in data]
                        if _is_degenerate_polygon(points):
                            report.skipped += 1
                            report.add(f"degenerate_roi path={source_rel} index={zone_index}")
                            continue
                        polygon_geometry = dict(legacy_1000x750_to_normalized(points, "polygon"))
                        normalized_points = polygon_geometry.get("points")
                        if not isinstance(normalized_points, list):
                            raise TypeError("normalized polygon points missing")
                        non_identical = len(set(normalized_points))
                        if non_identical < 3:
                            report.skipped += 1
                            report.add(f"degenerate_roi_normalized path={source_rel} index={zone_index}")
                            continue
                        geometry = polygon_geometry
                        model_zone_type = ZoneType.polygon
                    elif zone_type == "rect":
                        if not isinstance(data, list | tuple) or len(data) != 4:
                            raise TypeError("rect data must have four values")
                        rect = (float(data[0]), float(data[1]), float(data[2]), float(data[3]))
                        rect_geometry = dict(legacy_1000x750_to_normalized(rect, "rect"))
                        raw_rect_width = rect_geometry.get("width", 0.0)
                        raw_rect_height = rect_geometry.get("height", 0.0)
                        rect_width = raw_rect_width if isinstance(raw_rect_width, int | float) else 0.0
                        rect_height = raw_rect_height if isinstance(raw_rect_height, int | float) else 0.0
                        if rect_width <= 0 or rect_height <= 0:
                            report.skipped += 1
                            report.add(f"degenerate_roi_rect path={source_rel} index={zone_index}")
                            continue
                        geometry = rect_geometry
                        model_zone_type = ZoneType.rect
                    else:
                        report.conflicts += 1
                        report.add(f"corrupted_roi path={source_rel} index={zone_index} error=unsupported_type")
                        continue
                except (TypeError, ValueError, IndexError) as exc:
                    report.conflicts += 1
                    report.add(f"corrupted_roi path={source_rel} index={zone_index} error={exc.__class__.__name__}")
                    continue
                geometry = dict(geometry)
                geometry["source"] = {"width": LEGACY_RUNTIME_WIDTH, "height": LEGACY_RUNTIME_HEIGHT, "path": source_rel, "index": zone_index}
                existing_roi = None
                if not dry_run and scene is not None:
                    for roi in db.scalars(select(ROI).where(ROI.scene_id == scene.id)).all():
                        if _roi_source_matches(roi, source_rel, zone_index):
                            existing_roi = roi
                            break
                roi_name = f"Legacy ROI {zone_index + 1}"
                if existing_roi is None:
                    report.inserted += 1
                    report.add(f"roi_insert camera_ip={camera.ip} scene={scene_name!r} index={zone_index} type={zone_type}")
                    if not dry_run and scene is not None:
                        db.add(ROI(scene_id=scene.id, name=roi_name, zone_type=model_zone_type, geometry=geometry, normalized_coords=True, color=None))
                elif existing_roi.geometry != geometry or existing_roi.name != roi_name:
                    report.updated += 1
                    report.add(f"roi_update camera_ip={camera.ip} scene={scene_name!r} index={zone_index} type={zone_type}")
                    if not dry_run:
                        existing_roi.name = roi_name
                        existing_roi.zone_type = model_zone_type
                        existing_roi.geometry = geometry
                        existing_roi.normalized_coords = True
                else:
                    report.skipped += 1
                    report.add(f"roi_exists_unchanged camera_ip={camera.ip} scene={scene_name!r} index={zone_index}")
        if not dry_run:
            db.commit()
    return report


def migrate_alarm_config(dry_run: bool = False) -> MigrationReport:
    report = MigrationReport()
    settings = get_settings()
    alarm_config, duplicate_keys = _legacy_config_dict("ALARM_CONFIG")
    wechat_config, _ = _legacy_config_dict("WECHAT_CONFIG")
    merged_alarm = {**settings.alarm_config_overrides, **alarm_config}
    detectors = {key: merged_alarm.get(key) for key in ["enable_yolo_detection", "enable_image_comparison", "detection_mode", "yolo_weight", "image_weight", "human_filter_enabled"] if key in merged_alarm}
    area_config = {key: merged_alarm.get(key) for key in ["threshold", "diff_threshold", "min_contour_area", "area_ratio_threshold", "min_area_ratio", "max_area_ratio", "max_single_object_area"] if key in merged_alarm}
    duration_config = {key: merged_alarm.get(key) for key in ["interval_minutes", "static_wait_minutes", "min_stay_frames"] if key in merged_alarm}
    area_config["detectors"] = detectors
    duration_config["detectors"] = detectors
    for key in duplicate_keys:
        if key in {"max_brightness", "min_std"}:
            report.add(f"duplicate_key_effective_value key={key} value={merged_alarm.get(key)!r}")
    _ensure_schema()
    with SessionLocal() as db:
        cameras = list(db.scalars(select(Camera)).all())
        dry_run_camera_rows: list[_CameraRow] = []
        if dry_run and not cameras:
            dry_run_camera_rows, invalid_report = _camera_rows_for_migration(db, dry_run=True)
            report.skipped += invalid_report.skipped
            report.details.extend(invalid_report.details)
        camera_targets: list[Camera | _CameraRow] = [*cameras] if cameras else [*dry_run_camera_rows]
        if not camera_targets:
            report.skipped += 1
            report.add("rules_skipped_no_cameras")
        for camera in camera_targets:
            for rule_type, config in [(RuleType.obstruction_area, area_config), (RuleType.obstruction_duration, duration_config)]:
                existing = None if camera.id is None or camera.id < 0 else db.scalar(select(Rule).where(Rule.camera_id == camera.id, Rule.roi_id.is_(None), Rule.rule_type == rule_type))
                if existing is None:
                    report.inserted += 1
                    report.add(f"rule_insert camera_ip={camera.ip} type={rule_type.value}")
                    if not dry_run:
                        db.add(Rule(camera_id=camera.id, roi_id=None, rule_type=rule_type, config=config, enabled=True, priority=100))
                elif existing.config != config or not existing.enabled or existing.priority != 100:
                    report.updated += 1
                    report.add(f"rule_update camera_ip={camera.ip} type={rule_type.value}")
                    if not dry_run:
                        existing.config = config
                        existing.enabled = True
                        existing.priority = 100
                else:
                    report.skipped += 1
                    report.add(f"rule_exists_unchanged camera_ip={camera.ip} type={rule_type.value}")
        enabled = bool(wechat_config.get("enabled", False))
        webhook_exists = bool(wechat_config.get("webhook_url"))
        group = db.scalar(select(NotificationGroup).where(NotificationGroup.name == NOTIFICATION_GROUP_NAME))
        if group is None:
            report.inserted += 1
            report.add(f"notification_group_insert name={NOTIFICATION_GROUP_NAME!r} enabled={enabled} webhook_exists={webhook_exists}")
            if not dry_run:
                group = NotificationGroup(name=NOTIFICATION_GROUP_NAME, channels={}, members={}, enabled=enabled)
                db.add(group)
                db.flush()
        elif group.enabled != enabled:
            report.updated += 1
            report.add(f"notification_group_update name={NOTIFICATION_GROUP_NAME!r} enabled={enabled} webhook_exists={webhook_exists}")
            if not dry_run:
                group.enabled = enabled
        else:
            report.skipped += 1
            report.add(f"notification_group_exists_unchanged name={NOTIFICATION_GROUP_NAME!r} webhook_exists={webhook_exists}")
        group_id = group.id if group is not None else None
        if dry_run and group is None:
            report.inserted += 1
            report.add(f"notification_channel_insert type=wecom enabled={enabled} secret_ref={WECOM_SECRET_REF}")
        elif group_id is not None:
            channel = db.scalar(select(NotificationChannel).where(NotificationChannel.group_id == group_id, NotificationChannel.channel_type == NotificationChannelType.wecom))
            channel_config = {"webhook_url_secret_ref": WECOM_SECRET_REF}
            if channel is None:
                report.inserted += 1
                report.add(f"notification_channel_insert type=wecom enabled={enabled} secret_ref={WECOM_SECRET_REF}")
                if not dry_run:
                    db.add(NotificationChannel(group_id=group_id, channel_type=NotificationChannelType.wecom, config=channel_config, enabled=enabled))
            elif channel.enabled != enabled or channel.config != channel_config:
                report.updated += 1
                report.add(f"notification_channel_update type=wecom enabled={enabled} secret_ref={WECOM_SECRET_REF}")
                if not dry_run:
                    channel.enabled = enabled
                    channel.config = channel_config
            else:
                report.skipped += 1
                report.add("notification_channel_exists_unchanged type=wecom")
        if not dry_run:
            db.commit()
    return report


def migrate_all(dry_run: bool = False) -> FullMigrationReport:
    cameras = migrate_cameras(dry_run=dry_run)
    scenes = migrate_scenes_and_baselines(dry_run=dry_run)
    rois = migrate_rois(dry_run=dry_run)
    rules = migrate_alarm_config(dry_run=dry_run)
    return FullMigrationReport(cameras=cameras, scenes=scenes, rois=rois, rules=rules, dry_run=dry_run)


def report_to_dict(report: MigrationReport | FullMigrationReport) -> dict[str, Any]:
    return asdict(report)
