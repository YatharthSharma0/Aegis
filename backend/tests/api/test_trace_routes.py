"""Trace HTTP endpoints (TestClient integration, against the SQLite test DB)."""

from fastapi.testclient import TestClient

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


def test_health_alias(client: TestClient):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_trace_requires_authentication(client: TestClient):
    assert client.post("/api/v1/trace", json={"address": SEED}).status_code == 401
    assert client.get("/api/v1/trace/x").status_code == 401


def test_post_trace_returns_202_and_a_handle(client: TestClient, officer_headers):
    resp = client.post(
        "/api/v1/trace", json={"address": SEED, "case_id": "FIR-42"}, headers=officer_headers
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["stream_url"].endswith("/stream")
    assert len(body["trace_id"]) == 32


def test_full_flow_status_then_graph(client: TestClient, officer_headers):
    trace_id = client.post(
        "/api/v1/trace", json={"address": SEED}, headers=officer_headers
    ).json()["trace_id"]

    status = client.get(f"/api/v1/trace/{trace_id}", headers=officer_headers)
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "done"
    assert body["result_hash"].startswith("aegis.engine.v1:")
    assert body["chain"] == "tron"
    top = body["result"]["vasp_candidates"][0]
    assert top["name"] == "DemoExchange"
    assert top["verified"] is True
    assert top["confidence_terms"]["source_score"] == "1.0000"
    assert any(e["reason"] == "mixer_like" for e in body["result"]["trail_events"])

    graph = client.get(f"/api/v1/trace/{trace_id}/graph", headers=officer_headers).json()
    assert graph["trace_id"] == trace_id
    assert {e["from"] for e in graph["edges"]} <= {n["id"] for n in graph["nodes"]}
    seed_edge = next(e for e in graph["edges"] if e["from"] == SEED)
    assert seed_edge["asset"] == "USDT"
    assert seed_edge["taint"] == "1.000000000000"


def test_invalid_address_is_400_with_error_envelope(client: TestClient, officer_headers):
    resp = client.post("/api/v1/trace", json={"address": "nope"}, headers=officer_headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_request"
    assert resp.json()["error"]["details"]["address"] == "nope"


def test_unknown_trace_is_404(client: TestClient, officer_headers):
    resp = client.get(
        "/api/v1/trace/00000000000000000000000000000000", headers=officer_headers
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_unknown_body_field_is_rejected(client: TestClient, officer_headers):
    resp = client.post(
        "/api/v1/trace", json={"address": SEED, "surprise": 1}, headers=officer_headers
    )
    assert resp.status_code == 422


def test_openapi_is_served(client: TestClient):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/trace" in schema["paths"]
    assert "/api/v1/trace/{trace_id}/graph" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
