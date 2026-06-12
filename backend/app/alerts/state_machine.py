from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import WorkOrder, WorkOrderStatus


class InvalidStateTransition(Exception):
    """Raised when a work-order state transition is not allowed."""

    def __init__(self, current: WorkOrderStatus, target: WorkOrderStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid transition: {current.value} -> {target.value}"
        )


# Allowed transitions map: current -> set of allowed target statuses
_ALLOWED_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    WorkOrderStatus.open: {WorkOrderStatus.in_progress, WorkOrderStatus.cancelled},
    WorkOrderStatus.in_progress: {
        WorkOrderStatus.closed,
        WorkOrderStatus.open,
        WorkOrderStatus.cancelled,
    },
    # Terminal states — no outgoing transitions
    WorkOrderStatus.closed: set(),
    WorkOrderStatus.cancelled: set(),
}


class WorkOrderStateMachine:
    """Validates and executes work-order state transitions.

    Allowed transitions:
        open       -> in_progress  (operator picks up)
        open       -> cancelled    (admin only)
        in_progress -> closed      (resolved)
        in_progress -> open        (escalation / return)
        in_progress -> cancelled   (admin only)

    ``closed`` and ``cancelled`` are terminal states.
    """

    @staticmethod
    def can_transition(
        current: WorkOrderStatus, target: WorkOrderStatus
    ) -> bool:
        """Return True if the transition is allowed."""
        return target in _ALLOWED_TRANSITIONS.get(current, set())

    @staticmethod
    def transition(
        work_order: WorkOrder,
        target: WorkOrderStatus,
        user_id: int | None = None,
        notes: str | None = None,
        db: Session | None = None,
    ) -> WorkOrder:
        """Execute a state transition on *work_order*.

        Raises ``InvalidStateTransition`` when the transition is disallowed.
        If *db* is provided the change is committed and the instance refreshed.
        """
        current = WorkOrderStatus(work_order.status)

        if not WorkOrderStateMachine.can_transition(current, target):
            raise InvalidStateTransition(current, target)

        work_order.status = target

        if notes is not None:
            work_order.notes = notes

        if user_id is not None:
            work_order.assigned_to = user_id

        if db is not None:
            db.commit()
            db.refresh(work_order)

        return work_order


def get_open_work_order_for_alert(
    alert_id: int, db: Session
) -> WorkOrder | None:
    """Return the first non-terminal work order for *alert_id*, if any."""
    stmt = (
        select(WorkOrder)
        .where(
            WorkOrder.alert_id == alert_id,
            WorkOrder.status.in_(
                [WorkOrderStatus.open, WorkOrderStatus.in_progress]
            ),
        )
        .order_by(WorkOrder.id)
        .limit(1)
    )
    result = db.scalar(stmt)
    return result
