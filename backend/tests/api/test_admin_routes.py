"""Admin audit endpoint + RBAC."""

from fastapi.testclient import TestClient

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


def test_audit_requires_admin(client: TestClient, officer_headers):
    assert client.get("/api/v1/admin/audit").status_code == 401
    forbidden = client.get("/api/v1/admin/audit", headers=officer_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"


def test_audit_lists_trace_activity_and_verifies(
    client: TestClient, officer_headers, admin_headers, drain
):
    trace_id = client.post(
        "/api/v1/trace", json={"address": SEED}, headers=officer_headers
    ).json()["trace_id"]
    drain()
    client.get(f"/api/v1/trace/{trace_id}", headers=officer_headers)

    resp = client.get("/api/v1/admin/audit", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification"]["ok"] is True
    assert body["verification"]["checked"] >= 4
    actions = {e["action"] for e in body["entries"]}
    assert {"trace.start", "trace.claimed", "trace.complete", "trace.read"} <= actions
    start = next(e for e in body["entries"] if e["action"] == "trace.start")
    assert start["trace_id"] == trace_id
    assert start["actor_role"] == "officer"
    assert start["request_id"]


def test_response_carries_a_request_id_header(client: TestClient):
    resp = client.get("/api/v1/health")
    assert resp.headers.get("X-Request-ID")


def test_supplied_request_id_is_echoed(client: TestClient):
    resp = client.get("/api/v1/health", headers={"X-Request-ID": "trace-me-123"})
    assert resp.headers["X-Request-ID"] == "trace-me-123"
