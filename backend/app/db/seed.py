from __future__ import annotations

from sqlalchemy import select

from backend.app.auth.password import hash_password
from backend.app.db.session import SessionLocal, engine
from backend.app.models import Base, User, UserRole


def seed_default_admin() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing_user = db.scalar(select(User).limit(1))
        if existing_user is not None:
            return
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            display_name="Administrator",
            role=UserRole.admin,
            enabled=True,
        )
        db.add(admin)
        db.commit()


if __name__ == "__main__":
    seed_default_admin()
