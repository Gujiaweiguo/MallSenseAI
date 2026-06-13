from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.api.utils import commit_refresh, get_or_404, paginate, set_if_provided
from backend.app.db.session import get_db
from backend.app.models import NotificationChannel, NotificationChannelType, NotificationGroup, UserRole
from backend.app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationGroupCreate,
    NotificationGroupResponse,
    NotificationGroupUpdate,
)

router = APIRouter(prefix="/notification-groups", tags=["notifications"], dependencies=[Depends(get_current_user)])


# ---------------------------------------------------------------------------
# Notification Groups CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=list[NotificationGroupResponse])
def list_notification_groups(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[NotificationGroup]:
    stmt = select(NotificationGroup).options(selectinload(NotificationGroup.notification_channels)).order_by(NotificationGroup.id)
    return paginate(stmt, db, skip, limit)


@router.get("/{group_id}", response_model=NotificationGroupResponse)
def get_notification_group(group_id: int, db: Session = Depends(get_db)) -> NotificationGroup:
    stmt = select(NotificationGroup).options(selectinload(NotificationGroup.notification_channels)).where(NotificationGroup.id == group_id)
    group = db.scalars(stmt).first()
    if group is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="NotificationGroup not found")
    return group


@router.post(
    "",
    response_model=NotificationGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def create_notification_group(payload: NotificationGroupCreate, db: Session = Depends(get_db)) -> NotificationGroup:
    group = NotificationGroup(
        name=payload.name,
        channels={"severities": payload.severities},
        members={},
        enabled=payload.enabled,
    )
    db.add(group)
    db.flush()
    # Eagerly load channels (empty list for new group)
    _ = group.notification_channels  # noqa: F841
    return commit_refresh(db, group)


@router.put(
    "/{group_id}",
    response_model=NotificationGroupResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def update_notification_group(
    group_id: int,
    payload: NotificationGroupUpdate,
    db: Session = Depends(get_db),
) -> NotificationGroup:
    group = get_notification_group(group_id, db)
    if payload.name is not None:
        group.name = payload.name
    if payload.severities is not None:
        group.channels = {**group.channels, "severities": payload.severities}
    if payload.enabled is not None:
        group.enabled = payload.enabled
    db.flush()
    return commit_refresh(db, group)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def delete_notification_group(group_id: int, db: Session = Depends(get_db)) -> None:
    group = get_notification_group(group_id, db)
    db.delete(group)
    db.commit()


# ---------------------------------------------------------------------------
# Notification Channels CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/{group_id}/channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def create_notification_channel(
    group_id: int,
    payload: NotificationChannelCreate,
    db: Session = Depends(get_db),
) -> NotificationChannel:
    # Verify group exists
    get_notification_group(group_id, db)
    channel = NotificationChannel(
        group_id=group_id,
        channel_type=payload.channel_type,
        config=payload.config,
        enabled=payload.enabled,
    )
    db.add(channel)
    return commit_refresh(db, channel)


@router.put(
    "/channels/{channel_id}",
    response_model=NotificationChannelResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def update_notification_channel(
    channel_id: int,
    payload: NotificationChannelUpdate,
    db: Session = Depends(get_db),
) -> NotificationChannel:
    channel = db.get(NotificationChannel, channel_id)
    if channel is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="NotificationChannel not found")
    data = payload.model_dump(exclude_unset=True)
    set_if_provided(channel, data)
    return commit_refresh(db, channel)


@router.delete(
    "/channels/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def delete_notification_channel(channel_id: int, db: Session = Depends(get_db)) -> None:
    channel = db.get(NotificationChannel, channel_id)
    if channel is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="NotificationChannel not found")
    db.delete(channel)
    db.commit()


# ---------------------------------------------------------------------------
# Test notification send
# ---------------------------------------------------------------------------


@router.post(
    "/channels/{channel_id}/test",
    dependencies=[Depends(require_role(UserRole.operator))],
)
async def test_notification_channel(channel_id: int, db: Session = Depends(get_db)) -> dict[str, int | bool]:
    channel = db.get(NotificationChannel, channel_id)
    if channel is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="NotificationChannel not found")

    from backend.app.notifications.service import NotificationService
    from backend.app.db.session import SessionLocal

    service = NotificationService(SessionLocal)
    success = await service.send_to_channel(
        channel.channel_type,
        channel.config,
        "### 🧪 Test Notification\n> This is a test message from MallSenseAI.",
    )
    return {"channel_id": channel_id, "success": success}
