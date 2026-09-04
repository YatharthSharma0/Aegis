"""Auth HTTP endpoints + route protection."""

from fastapi.testclient import TestClient

from app.api.deps import get_account_service
from app.domain.accounts import Role

EMAIL = "priya@mahacyber.gov.in"
PASSWORD = "password12345"


def _seed_officer() -> None:
    get_account_service().create_user(
        email=EMAIL, full_name="Priya K", role=Role.OFFICER, password=PASSWORD, unit="Pune"
    )


def test_login_returns_a_token_pair(client: TestClient):
    _seed_officer()
    resp = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "officer"
    assert body["expires_in"] == 900
    assert body["access_token"] and body["refresh_token"]


def test_login_wrong_password_is_401(client: TestClient):
    _seed_officer()
    resp = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "nope"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


def test_login_unknown_user_is_401(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "x@y.z", "password": "whatever1"})
    assert resp.status_code == 401


def test_me_returns_the_current_user(client: TestClient):
    _seed_officer()
    token = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    ).json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    assert me.json()["unit"] == "Pune"


def test_me_without_a_token_is_401(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_the_pair(client: TestClient):
    _seed_officer()
    first = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    ).json()

    second = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert second.status_code == 200
    assert second.json()["refresh_token"] != first["refresh_token"]

    # reusing the burned refresh token fails
    reuse = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert reuse.status_code == 401


def test_an_access_token_cannot_be_used_to_refresh(client: TestClient):
    _seed_officer()
    access = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    ).json()["access_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


def test_malformed_bearer_is_401(client: TestClient, officer_headers):
    ok = client.post("/api/v1/trace", json={"address": "T" + "0" * 33}, headers=officer_headers)
    assert ok.status_code in (400, 422)  # got past auth
    bad = client.post(
        "/api/v1/trace",
        json={"address": "T" + "0" * 33},
        headers={"Authorization": "Bearer garbage.token.here"},
    )
    assert bad.status_code == 401
