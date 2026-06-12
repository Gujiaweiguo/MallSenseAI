from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.api.utils import Camera, ROI, Rule, commit_refresh, ensure_exists, get_or_404, paginate, select, set_if_provided
from backend.app.db.session import get_db
from backend.app.models import UserRole
from backend.app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[RuleResponse])
def list_rules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Rule]:
    return paginate(select(Rule).order_by(Rule.id), db, skip, limit)


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db)) -> Rule:
    return get_or_404(db, Rule, rule_id)


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.operator))])
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)) -> Rule:
    ensure_exists(db, Camera, payload.camera_id)
    ensure_exists(db, ROI, payload.roi_id)
    rule = Rule(**payload.model_dump())
    db.add(rule)
    return commit_refresh(db, rule)


@router.put("/{rule_id}", response_model=RuleResponse, dependencies=[Depends(require_role(UserRole.operator))])
def update_rule(rule_id: int, payload: RuleUpdate, db: Session = Depends(get_db)) -> Rule:
    rule = get_or_404(db, Rule, rule_id)
    data = payload.model_dump(exclude_unset=True)
    ensure_exists(db, Camera, data.get("camera_id"))
    ensure_exists(db, ROI, data.get("roi_id"))
    set_if_provided(rule, data)
    return commit_refresh(db, rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.operator))])
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> None:
    rule = get_or_404(db, Rule, rule_id)
    db.delete(rule)
    db.commit()
