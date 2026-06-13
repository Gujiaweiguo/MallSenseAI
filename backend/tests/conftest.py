"""Shared test fixtures for backend API tests.

All test modules that need a FastAPI TestClient with an isolated SQLite
database should rely on this conftest instead of setting up their own
engines or overriding ``get_db`` at module level.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.auth.password import hash_password
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Base, User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Single override — set once, shared by all test modules.
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(
        User(
            username="admin",
            password_hash=hash_password("admin123"),
            display_name="Admin",
            role="admin",
            enabled=True,
        )
    )
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
