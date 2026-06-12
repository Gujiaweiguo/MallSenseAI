from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.auth.password import hash_password
from backend.app.api.utils import User, commit_refresh, get_or_404, paginate, select, set_if_provided
from backend.app.db.session import get_db
from backend.app.models import UserRole
from backend.app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[User]:
    return paginate(select(User).order_by(User.id), db, skip, limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    return get_or_404(db, User, user_id)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.admin))])
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    data = payload.model_dump(exclude={"password"})
    user = User(**data, password_hash=hash_password(payload.password))
    db.add(user)
    return commit_refresh(db, user)


@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role(UserRole.admin))])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = get_or_404(db, User, user_id)
    data = payload.model_dump(exclude_unset=True, exclude={"password"})
    set_if_provided(user, data)
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    return commit_refresh(db, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.admin))])
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    user = get_or_404(db, User, user_id)
    db.delete(user)
    db.commit()
