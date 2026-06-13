from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.alerts.service import AlertService, InvalidAlertTransition
from backend.app.alerts.state_machine import InvalidStateTransition, WorkOrderStateMachine
from backend.app.api.utils import User, WorkOrder, get_or_404
from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.db.session import get_db
from backend.app.models import UserRole, WorkOrderStatus
from backend.app.schemas.alert import AlertResponse
from backend.app.schemas.work_order import WorkOrderResponse

router = APIRouter(tags=["alert-workflow"], dependencies=[Depends(get_current_user)])


# ------------------------------------------------------------------
# Request / response schemas local to this router
# ------------------------------------------------------------------


class FalsePositiveRequest(BaseModel):
    reason: str = ""


class ResolveRequest(BaseModel):
    notes: str = ""


class AssignRequest(BaseModel):
    user_id: int


class TransitionRequest(BaseModel):
    target: WorkOrderStatus
    notes: str | None = None


class BatchAlertRequest(BaseModel):
    alert_ids: list[int]
    action: str  # "confirm" | "false_positive" | "resolve"


class BatchFailureItem(BaseModel):
    id: int
    error: str


class BatchAlertResponse(BaseModel):
    processed: int
    failed: list[BatchFailureItem]


# ------------------------------------------------------------------
# Alert lifecycle endpoints
# ------------------------------------------------------------------


@router.post(
    "/alerts/{alert_id}/confirm",
    response_model=AlertResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def confirm_alert(alert_id: int, db: Session = Depends(get_db)) -> dict:
    """Confirm a pending alert and auto-create a work order."""
    try:
        return AlertService.confirm_alert(alert_id, db)
    except InvalidAlertTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/alerts/{alert_id}/false-positive",
    response_model=AlertResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def mark_false_positive(
    alert_id: int,
    payload: FalsePositiveRequest = FalsePositiveRequest(),
    db: Session = Depends(get_db),
) -> dict:
    """Mark an alert as false positive."""
    try:
        return AlertService.mark_false_positive(alert_id, db, reason=payload.reason)
    except InvalidAlertTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=AlertResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def resolve_alert(
    alert_id: int,
    payload: ResolveRequest = ResolveRequest(),
    db: Session = Depends(get_db),
) -> dict:
    """Resolve a confirmed alert."""
    try:
        return AlertService.resolve_alert(alert_id, db, notes=payload.notes)
    except InvalidAlertTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


# ------------------------------------------------------------------
# Batch alert endpoints
# ------------------------------------------------------------------


@router.post(
    "/alerts/batch",
    response_model=BatchAlertResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def batch_alert_action(
    payload: BatchAlertRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Apply an action (confirm, false_positive, resolve) to multiple alerts.

    Each alert is processed independently; failures for individual alerts
    (e.g. invalid state transition) are collected and returned without
    aborting the entire batch.
    """
    valid_actions = {"confirm", "false_positive", "resolve"}
    if payload.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action '{payload.action}'. Must be one of {valid_actions}",
        )

    processed = 0
    failed: list[dict] = []

    for alert_id in payload.alert_ids:
        try:
            if payload.action == "confirm":
                AlertService.confirm_alert(alert_id, db)
            elif payload.action == "false_positive":
                AlertService.mark_false_positive(alert_id, db, reason="")
            elif payload.action == "resolve":
                AlertService.resolve_alert(alert_id, db, notes="")
            processed += 1
        except (InvalidAlertTransition, Exception) as exc:  # noqa: BLE001
            failed.append({"id": alert_id, "error": str(exc)})

    return {"processed": processed, "failed": failed}


# ------------------------------------------------------------------
# Work-order workflow endpoints
# ------------------------------------------------------------------


@router.post(
    "/work-orders/{work_order_id}/assign",
    response_model=WorkOrderResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def assign_work_order(
    work_order_id: int,
    payload: AssignRequest,
    db: Session = Depends(get_db),
) -> WorkOrder:
    """Assign an operator to a work order."""
    work_order = get_or_404(db, WorkOrder, work_order_id)
    # Verify the user exists and is active
    user = db.get(User, payload.user_id)
    if user is None or not user.enabled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User not found or inactive",
        )
    work_order.assigned_to = payload.user_id
    db.commit()
    db.refresh(work_order)
    return work_order


@router.post(
    "/work-orders/{work_order_id}/transition",
    response_model=WorkOrderResponse,
    dependencies=[Depends(require_role(UserRole.operator))],
)
def transition_work_order(
    work_order_id: int,
    payload: TransitionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrder:
    """Execute a work-order state transition.

    Cancellation requires admin role.
    """
    work_order = get_or_404(db, WorkOrder, work_order_id)

    # Enforce admin-only for cancellation
    if payload.target == WorkOrderStatus.cancelled:
        if current_user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can cancel work orders",
            )

    try:
        return WorkOrderStateMachine.transition(
            work_order,
            payload.target,
            user_id=current_user.id,
            notes=payload.notes,
            db=db,
        )
    except InvalidStateTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
