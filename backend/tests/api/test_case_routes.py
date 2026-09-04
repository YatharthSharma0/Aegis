"""Case-management HTTP endpoints."""

from fastapi.testclient import TestClient

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


def test_cases_require_auth(client: TestClient):
    assert client.get("/api/v1/cases").status_code == 401
    assert client.post("/api/v1/cases", json={"ref_no": "x", "title": "y"}).status_code == 401


def test_create_list_get_patch(client: TestClient, officer_headers):
    created = client.post(
        "/api/v1/cases",
        json={
            "ref_no": "FIR 9/2026",
            "title": "Pig butchering",
            "typology_hint": "investment_scam",
        },
        headers=officer_headers,
    )
    assert created.status_code == 201
    case_id = created.json()["id"]
    assert created.json()["status"] == "open"

    listed = client.get("/api/v1/cases", headers=officer_headers).json()
    assert any(c["id"] == case_id for c in listed)

    detail = client.get(f"/api/v1/cases/{case_id}", headers=officer_headers).json()
    assert detail["complaints"] == []
    assert detail["trace_runs"] == []

    patched = client.patch(
        f"/api/v1/cases/{case_id}", json={"status": "in_progress"}, headers=officer_headers
    )
    assert patched.json()["status"] == "in_progress"


def test_duplicate_ref_no_is_409(client: TestClient, officer_headers):
    body = {"ref_no": "DUP-1", "title": "A"}
    assert client.post("/api/v1/cases", json=body, headers=officer_headers).status_code == 201
    dup = client.post("/api/v1/cases", json=body, headers=officer_headers)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "conflict"


def test_get_unknown_case_is_404(client: TestClient, officer_headers):
    resp = client.get("/api/v1/cases/deadbeef", headers=officer_headers)
    assert resp.status_code == 404


def test_trace_can_be_linked_to_a_case_and_shows_in_detail(
    client: TestClient, officer_headers, drain
):
    case_id = client.post(
        "/api/v1/cases", json={"ref_no": "LINK-1", "title": "A"}, headers=officer_headers
    ).json()["id"]

    trace_id = client.post(
        "/api/v1/trace", json={"address": SEED, "case_id": case_id}, headers=officer_headers
    ).json()["trace_id"]
    drain()

    detail = client.get(f"/api/v1/cases/{case_id}", headers=officer_headers).json()
    assert [r["trace_id"] for r in detail["trace_runs"]] == [trace_id]
    assert detail["trace_runs"][0]["status"] == "done"


def test_trace_against_a_missing_case_is_404(client: TestClient, officer_headers):
    resp = client.post(
        "/api/v1/trace", json={"address": SEED, "case_id": "no-such-case"}, headers=officer_headers
    )
    assert resp.status_code == 404


def test_demo_complaint_can_be_attached_real_one_rejected(client: TestClient, officer_headers):
    case_id = client.post(
        "/api/v1/cases", json={"ref_no": "CMP-1", "title": "A"}, headers=officer_headers
    ).json()["id"]

    ok = client.post(
        f"/api/v1/cases/{case_id}/complaints",
        json={"source": "ncrp", "text": "fictional narrative", "is_demo": True},
        headers=officer_headers,
    )
    assert ok.status_code == 201
    assert ok.json()["is_demo"] is True

    bad = client.post(
        f"/api/v1/cases/{case_id}/complaints",
        json={"source": "manual", "text": "real text", "is_demo": False},
        headers=officer_headers,
    )
    assert bad.status_code == 400
