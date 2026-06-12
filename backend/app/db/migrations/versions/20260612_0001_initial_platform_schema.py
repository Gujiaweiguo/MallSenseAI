"""initial platform schema

Revision ID: 20260612_0001
Revises:
Create Date: 2026-06-12 00:00:00+00:00
"""
from __future__ import annotations

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260612_0001"
down_revision = None
branch_labels = None
depends_on = None


def _json_type():
    bind = op.get_bind()
    return postgresql.JSONB() if bind.dialect.name == "postgresql" else sa.JSON()


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _create_enum(name: str, values: Iterable[str]) -> sa.Enum:
    enum_type = sa.Enum(*values, name=name)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        enum_type.create(bind, checkfirst=True)
    return enum_type


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    camera_status = _create_enum("camera_status", ["active", "inactive", "maintenance", "error"])
    zone_type = _create_enum("zone_type", ["polygon", "rect"])
    rule_type = _create_enum("rule_type", ["obstruction_duration", "obstruction_area", "litter", "fire_smoke"])
    alert_type = _create_enum("alert_type", ["obstruction_duration", "obstruction_area", "litter", "fire_smoke"])
    alert_severity = _create_enum("alert_severity", ["low", "medium", "high", "critical"])
    alert_status = _create_enum("alert_status", ["pending", "confirmed", "false_positive", "resolved"])
    work_order_status = _create_enum("work_order_status", ["open", "in_progress", "closed", "cancelled"])
    user_role = _create_enum("user_role", ["admin", "operator", "viewer"])
    notification_channel_type = _create_enum("notification_channel_type", ["wecom", "sms", "email"])
    detector_type = _create_enum("detector_type", ["image_compare", "yolo", "blue_box"])
    json_type = _json_type()

    if not _has_table("cameras"):
        op.create_table(
            "cameras",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("location", sa.String(255), nullable=False),
            sa.Column("ip", sa.String(64), nullable=False),
            sa.Column("port", sa.Integer(), nullable=False, server_default="80"),
            sa.Column("username", sa.String(128), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("status", camera_status, nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("ip", "port", name="uq_cameras_ip_port"),
        )
        op.create_index("ix_cameras_location", "cameras", ["location"])
        op.create_index("ix_cameras_status", "cameras", ["status"])

    if not _has_table("scenes"):
        op.create_table(
            "scenes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("baseline_image_path", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_scenes_camera_id", "scenes", ["camera_id"])

    if not _has_table("rois"):
        op.create_table(
            "rois",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("scene_id", sa.Integer(), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("zone_type", zone_type, nullable=False),
            sa.Column("geometry", json_type, nullable=False),
            sa.Column("normalized_coords", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("color", sa.String(32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_rois_scene_id", "rois", ["scene_id"])
        op.create_index("ix_rois_zone_type", "rois", ["zone_type"])

    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("username", sa.String(128), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(128), nullable=False),
            sa.Column("role", user_role, nullable=False, server_default="viewer"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("username", name="uq_users_username"),
        )
        op.create_index("ix_users_role", "users", ["role"])

    if not _has_table("rules"):
        op.create_table(
            "rules",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
            sa.Column("roi_id", sa.Integer(), sa.ForeignKey("rois.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rule_type", rule_type, nullable=False),
            sa.Column("config", json_type, nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_rules_camera_id", "rules", ["camera_id"])
        op.create_index("ix_rules_roi_id", "rules", ["roi_id"])
        op.create_index("ix_rules_enabled_priority", "rules", ["enabled", "priority"])

    if not _has_table("alerts"):
        op.create_table(
            "alerts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
            sa.Column("roi_id", sa.Integer(), sa.ForeignKey("rois.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rule_id", sa.Integer(), sa.ForeignKey("rules.id", ondelete="SET NULL"), nullable=True),
            sa.Column("alert_type", alert_type, nullable=False),
            sa.Column("severity", alert_severity, nullable=False, server_default="medium"),
            sa.Column("status", alert_status, nullable=False, server_default="pending"),
            sa.Column("evidence_image_path", sa.String(512), nullable=True),
            sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_alerts_camera_id", "alerts", ["camera_id"])
        op.create_index("ix_alerts_roi_id", "alerts", ["roi_id"])
        op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
        op.create_index("ix_alerts_status_detected_at", "alerts", ["status", "detected_at"])

    if not _has_table("work_orders"):
        op.create_table(
            "work_orders",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("status", work_order_status, nullable=False, server_default="open"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_work_orders_alert_id", "work_orders", ["alert_id"])
        op.create_index("ix_work_orders_assigned_to", "work_orders", ["assigned_to"])
        op.create_index("ix_work_orders_status", "work_orders", ["status"])

    if not _has_table("notification_groups"):
        op.create_table(
            "notification_groups",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("channels", json_type, nullable=False),
            sa.Column("members", json_type, nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("name", name="uq_notification_groups_name"),
        )

    if not _has_table("notification_channels"):
        op.create_table(
            "notification_channels",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("group_id", sa.Integer(), sa.ForeignKey("notification_groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_type", notification_channel_type, nullable=False),
            sa.Column("config", json_type, nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index("ix_notification_channels_group_id", "notification_channels", ["group_id"])
        op.create_index("ix_notification_channels_type", "notification_channels", ["channel_type"])

    if not _has_table("detection_events"):
        op.create_table(
            "detection_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
            sa.Column("roi_id", sa.Integer(), sa.ForeignKey("rois.id", ondelete="SET NULL"), nullable=True),
            sa.Column("detector_type", detector_type, nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("evidence_path", sa.String(512), nullable=True),
            sa.Column("metadata", json_type, nullable=False),
            sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_detection_events_camera_id", "detection_events", ["camera_id"])
        op.create_index("ix_detection_events_roi_id", "detection_events", ["roi_id"])
        op.create_index("ix_detection_events_detected_at", "detection_events", ["detected_at"])


def downgrade() -> None:
    for table_name in [
        "detection_events",
        "notification_channels",
        "notification_groups",
        "work_orders",
        "alerts",
        "rules",
        "users",
        "rois",
        "scenes",
        "cameras",
    ]:
        if _has_table(table_name):
            op.drop_table(table_name)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_name in [
            "detector_type",
            "notification_channel_type",
            "user_role",
            "work_order_status",
            "alert_status",
            "alert_severity",
            "alert_type",
            "rule_type",
            "zone_type",
            "camera_status",
        ]:
            op.execute(f"DROP TYPE IF EXISTS {enum_name}")
