from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.api.utils import Alert, User, WorkOrder, commit_refresh, ensure_exists, get_or_404, paginate, select, set_if_provided
from backend.app.db.session import get_db
from backend.app.models import UserRole
from backend.app.schemas.work_order import WorkOrderCreate, WorkOrderResponse, WorkOrderUpdate

router = APIRouter(prefix="/work-orders", tags=["work-orders"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[WorkOrderResponse])
def list_work_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[WorkOrder]:
    return paginate(select(WorkOrder).order_by(WorkOrder.id), db, skip, limit)


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(work_order_id: int, db: Session = Depends(get_db)) -> WorkOrder:
    return get_or_404(db, WorkOrder, work_order_id)


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.admin))])
def create_work_order(payload: WorkOrderCreate, db: Session = Depends(get_db)) -> WorkOrder:
    ensure_exists(db, Alert, payload.alert_id)
    ensure_exists(db, User, payload.assigned_to)
    work_order = WorkOrder(**payload.model_dump())
    db.add(work_order)
    return commit_refresh(db, work_order)


@router.put("/{work_order_id}", response_model=WorkOrderResponse, dependencies=[Depends(require_role(UserRole.admin))])
def update_work_order(work_order_id: int, payload: WorkOrderUpdate, db: Session = Depends(get_db)) -> WorkOrder:
    work_order = get_or_404(db, WorkOrder, work_order_id)
    data = payload.model_dump(exclude_unset=True)
    ensure_exists(db, Alert, data.get("alert_id"))
    ensure_exists(db, User, data.get("assigned_to"))
    set_if_provided(work_order, data)
    return commit_refresh(db, work_order)


@router.patch("/{work_order_id}/status", response_model=WorkOrderResponse, dependencies=[Depends(require_role(UserRole.admin))])
def transition_work_order_status(work_order_id: int, payload: WorkOrderUpdate, db: Session = Depends(get_db)) -> WorkOrder:
    work_order = get_or_404(db, WorkOrder, work_order_id)
    if payload.status is not None:
        work_order.status = payload.status
    return commit_refresh(db, work_order)


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.admin))])
def delete_work_order(work_order_id: int, db: Session = Depends(get_db)) -> None:
    work_order = get_or_404(db, WorkOrder, work_order_id)
    db.delete(work_order)
    db.commit()
