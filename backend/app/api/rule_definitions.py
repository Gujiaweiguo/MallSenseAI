from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.utils import Rule, commit_refresh, get_or_404, paginate, select
from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.db.session import get_db
from backend.app.models import RuleDefinition, UserRole
from backend.app.schemas.rule_definition import RuleDefinitionCreate, RuleDefinitionResponse, RuleDefinitionUpdate

router = APIRouter(prefix="/rule-definitions", tags=["rule-definitions"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[RuleDefinitionResponse])
def list_rule_definitions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[RuleDefinition]:
    return paginate(select(RuleDefinition).order_by(RuleDefinition.id), db, skip, limit)


@router.get("/{definition_id}", response_model=RuleDefinitionResponse)
def get_rule_definition(definition_id: int, db: Session = Depends(get_db)) -> RuleDefinition:
    return get_or_404(db, RuleDefinition, definition_id)


@router.post("", response_model=RuleDefinitionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.operator))])
def create_rule_definition(payload: RuleDefinitionCreate, db: Session = Depends(get_db)) -> RuleDefinition:
    existing = db.execute(select(RuleDefinition).where(RuleDefinition.name == payload.name)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Definition '{payload.name}' already exists")
    definition = RuleDefinition(**payload.model_dump())
    db.add(definition)
    return commit_refresh(db, definition)


@router.put("/{definition_id}", response_model=RuleDefinitionResponse, dependencies=[Depends(require_role(UserRole.operator))])
def update_rule_definition(definition_id: int, payload: RuleDefinitionUpdate, db: Session = Depends(get_db)) -> RuleDefinition:
    definition = get_or_404(db, RuleDefinition, definition_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(definition, key, value)
    if "config" in data:
        assignments = list(db.scalars(select(Rule).where(Rule.definition_id == definition_id)).all())
        for assignment in assignments:
            assignment.config = definition.config
            assignment.rule_type = definition.rule_type
    return commit_refresh(db, definition)


@router.delete("/{definition_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.operator))])
def delete_rule_definition(definition_id: int, db: Session = Depends(get_db)) -> None:
    definition = get_or_404(db, RuleDefinition, definition_id)
    assignment_count = db.execute(select(Rule).where(Rule.definition_id == definition_id)).scalars().all()
    if assignment_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete definition with existing assignments")
    db.delete(definition)
    db.commit()
