"""Login -> bearer on every call -> refresh on expiry -> reject reuse.

The math (signing, TTL expiry, reuse detection) is already unit-tested
(`tests/security/test_tokens.py`, `tests/domain/test_accounts.py`); this
suite only proves the same behaviour holds over the real HTTP/CORS path.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


def test_login_then_me(client: httpx.Client, test_user: tuple[str, str]):
    email, password = test_user
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email


def test_wrong_password_is_rejected(client: httpx.Client, test_user: tuple[str, str]):
    email, _ = test_user
    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "definitely-wrong"}
    )
    assert resp.status_code == 401, resp.text


def test_protected_route_without_a_token_is_rejected(client: httpx.Client):
    resp = client.get("/api/v1/cases")
    assert resp.status_code in (401, 403), resp.text


def test_protected_route_with_a_malformed_token_is_rejected(client: httpx.Client):
    resp = client.get(
        "/api/v1/cases", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert resp.status_code == 401, resp.text


def test_refresh_rotates_the_token_and_rejects_reuse(
    client: httpx.Client, test_user: tuple[str, str]
):
    email, password = test_user
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    refresh_token = login.json()["refresh_token"]

    first_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first_refresh.status_code == 200, first_refresh.text
    rotated_token = first_refresh.json()["refresh_token"]
    assert rotated_token != refresh_token

    # Reusing the now-rotated-away token must fail: `revoke_refresh` burns
    # the presented jti on rotation (`AccountService.refresh`,
    # backend/app/domain/accounts.py) — this is per-token revocation, not
    # whole-chain reuse detection, so the token it rotated *to* stays valid.
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401, reuse.text

    still_valid = client.post("/api/v1/auth/refresh", json={"refresh_token": rotated_token})
    assert still_valid.status_code == 200, still_valid.text
