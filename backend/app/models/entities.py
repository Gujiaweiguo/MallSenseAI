from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.models.base import Base, TimestampMixin, utc_now

JsonDict = dict[str, Any]
JsonbType = JSONB().with_variant(JSON(), "sqlite")


class CameraStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"
    error = "error"


class ZoneType(str, enum.Enum):
    polygon = "polygon"
    rect = "rect"


class RuleType(str, enum.Enum):
    obstruction_duration = "obstruction_duration"
    obstruction_area = "obstruction_area"
    forbidden_zone = "forbidden_zone"
    litter = "litter"
    fire_smoke = "fire_smoke"


class AlertSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    false_positive = "false_positive"
    resolved = "resolved"


class WorkOrderStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"
    cancelled = "cancelled"


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class NotificationChannelType(str, enum.Enum):
    wecom = "wecom"
    sms = "sms"
    email = "email"


class DetectorType(str, enum.Enum):
    image_compare = "image_compare"
    yolo = "yolo"
    blue_box = "blue_box"


class Camera(Base, TimestampMixin):
    __tablename__ = "cameras"
    __table_args__ = (
        UniqueConstraint("ip", "port", name="uq_cameras_ip_port"),
        Index("ix_cameras_location", "location"),
        Index("ix_cameras_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    # NOTE: Despite the column name, this stores the plaintext camera password
    # (needed for HTTP/RTSP auth to the camera). Not bcrypt-hashed like User.password_hash.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CameraStatus] = mapped_column(Enum(CameraStatus, name="camera_status"), nullable=False, default=CameraStatus.active)

    scenes: Mapped[list["Scene"]] = relationship(back_populates="camera", cascade="all, delete-orphan")
    rules: Mapped[list["Rule"]] = relationship(back_populates="camera")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="camera")
    detection_events: Mapped[list["DetectionEvent"]] = relationship(back_populates="camera")


class Scene(Base, TimestampMixin):
    __tablename__ = "scenes"
    __table_args__ = (Index("ix_scenes_camera_id", "camera_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    baseline_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    camera: Mapped[Camera] = relationship(back_populates="scenes")
    rois: Mapped[list["ROI"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class ROI(Base, TimestampMixin):
    __tablename__ = "rois"
    __table_args__ = (
        Index("ix_rois_scene_id", "scene_id"),
        Index("ix_rois_zone_type", "zone_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(Enum(ZoneType, name="zone_type"), nullable=False)
    geometry: Mapped[JsonDict] = mapped_column(JsonbType, nullable=False)
    normalized_coords: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    scene: Mapped[Scene] = relationship(back_populates="rois")
    rules: Mapped[list["Rule"]] = relationship(back_populates="roi")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="roi")
    detection_events: Mapped[list["DetectionEvent"]] = relationship(back_populates="roi")


class Rule(Base, TimestampMixin):
    __tablename__ = "rules"
    __table_args__ = (
        Index("ix_rules_camera_id", "camera_id"),
        Index("ix_rules_roi_id", "roi_id"),
        Index("ix_rules_enabled_priority", "enabled", "priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    roi_id: Mapped[int | None] = mapped_column(ForeignKey("rois.id", ondelete="SET NULL"), nullable=True)
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType, name="rule_type"), nullable=False)
    config: Mapped[JsonDict] = mapped_column(JsonbType, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    camera: Mapped[Camera] = relationship(back_populates="rules")
    roi: Mapped[ROI | None] = relationship(back_populates="rules")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="rule")


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_camera_id", "camera_id"),
        Index("ix_alerts_roi_id", "roi_id"),
        Index("ix_alerts_rule_id", "rule_id"),
        Index("ix_alerts_status_detected_at", "status", "detected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    roi_id: Mapped[int | None] = mapped_column(ForeignKey("rois.id", ondelete="SET NULL"), nullable=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id", ondelete="SET NULL"), nullable=True)
    alert_type: Mapped[RuleType] = mapped_column(Enum(RuleType, name="alert_type"), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity, name="alert_severity"), nullable=False, default=AlertSeverity.medium)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, name="alert_status"), nullable=False, default=AlertStatus.pending)
    evidence_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_metadata: Mapped[JsonDict] = mapped_column("metadata", JsonbType, nullable=False, default=dict)

    camera: Mapped[Camera] = relationship(back_populates="alerts")
    roi: Mapped[ROI | None] = relationship(back_populates="alerts")
    rule: Mapped[Rule | None] = relationship(back_populates="alerts")
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="alert")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_role", "role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.viewer)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    assigned_work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="assigned_user")


class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"
    __table_args__ = (
        Index("ix_work_orders_alert_id", "alert_id"),
        Index("ix_work_orders_assigned_to", "assigned_to"),
        Index("ix_work_orders_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[WorkOrderStatus] = mapped_column(Enum(WorkOrderStatus, name="work_order_status"), nullable=False, default=WorkOrderStatus.open)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    alert: Mapped[Alert] = relationship(back_populates="work_orders")
    assigned_user: Mapped[User | None] = relationship(back_populates="assigned_work_orders")


class NotificationGroup(Base, TimestampMixin):
    __tablename__ = "notification_groups"
    __table_args__ = (UniqueConstraint("name", name="uq_notification_groups_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    channels: Mapped[JsonDict] = mapped_column(JsonbType, nullable=False, default=dict)
    members: Mapped[JsonDict] = mapped_column(JsonbType, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    notification_channels: Mapped[list["NotificationChannel"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (
        Index("ix_notification_channels_group_id", "group_id"),
        Index("ix_notification_channels_type", "channel_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("notification_groups.id", ondelete="CASCADE"), nullable=False)
    channel_type: Mapped[NotificationChannelType] = mapped_column(Enum(NotificationChannelType, name="notification_channel_type"), nullable=False)
    config: Mapped[JsonDict] = mapped_column(JsonbType, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    group: Mapped[NotificationGroup] = relationship(back_populates="notification_channels")


class DetectionEvent(Base):
    __tablename__ = "detection_events"
    __table_args__ = (
        Index("ix_detection_events_camera_id", "camera_id"),
        Index("ix_detection_events_roi_id", "roi_id"),
        Index("ix_detection_events_detected_at", "detected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    roi_id: Mapped[int | None] = mapped_column(ForeignKey("rois.id", ondelete="SET NULL"), nullable=True)
    detector_type: Mapped[DetectorType] = mapped_column(Enum(DetectorType, name="detector_type"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    event_metadata: Mapped[JsonDict] = mapped_column("metadata", JsonbType, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    camera: Mapped[Camera] = relationship(back_populates="detection_events")
    roi: Mapped[ROI | None] = relationship(back_populates="detection_events")


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_inspections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cameras_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
