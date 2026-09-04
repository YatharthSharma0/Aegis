"""Shared API-test fixtures: a TestClient plus helpers to authenticate."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_account_service
from app.domain.accounts import Role
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user() -> Callable[..., str]:
    """Return a factory: make_user(role=...) -> access token."""
    counter = {"n": 0}

    def _make(role: Role = Role.OFFICER, password: str = "password123") -> str:
        counter["n"] += 1
        email = f"user{counter['n']}@aegis.test"
        get_account_service().create_user(
            email=email, full_name="Test User", role=role, password=password
        )
        with TestClient(app) as c:
            resp = c.post("/api/v1/auth/login", json={"email": email, "password": password})
        return str(resp.json()["access_token"])

    return _make


@pytest.fixture
def officer_headers(make_user: Callable[..., str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_user(Role.OFFICER)}"}


@pytest.fixture
def admin_headers(make_user: Callable[..., str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_user(Role.ADMIN)}"}
