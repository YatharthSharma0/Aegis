"""Report + SAHYOG notice endpoints."""

from fastapi.testclient import TestClient

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


def _done_trace(client: TestClient, headers, drain) -> str:
    trace_id = client.post(
        "/api/v1/trace", json={"address": SEED}, headers=headers
    ).json()["trace_id"]
    drain()
    return trace_id


def test_report_requires_auth(client: TestClient):
    assert client.get("/api/v1/trace/x/report").status_code == 401


def test_report_on_a_finished_trace(client: TestClient, officer_headers, drain):
    trace_id = _done_trace(client, officer_headers, drain)
    resp = client.get(f"/api/v1/trace/{trace_id}/report", headers=officer_headers)
    assert resp.status_code == 200
    report = resp.json()

    assert report["report_type"] == "aegis.investigation_report.v1"
    assert report["header"]["trace_id"] == trace_id
    assert report["header"]["result_hash"].startswith("aegis.engine.v1:")
    assert report["header"]["generated_by"]  # the officer's email

    top = report["vasp_candidates"][0]
    assert top["name"] == "DemoExchange"
    assert top["verified"] is True
    # the confidence arithmetic is spelled out
    f = top["confidence_formula"]
    assert set(f["terms"]) == set(f["weights"])
    assert f["score"] == str(top["confidence"])

    assert report["fund_flow"][0]["from"] == SEED
    assert any(e["reason"] == "mixer_like" for e in report["trail_events"])
    assert report["data_sources"]  # provider snapshots cited
    assert "Bharatiya Sakshya Adhiniyam" in report["certification"]["statement"]
    assert report["certification"]["reproducibility_anchor"] == report["header"]["result_hash"]


def test_report_pdf_is_not_implemented(client: TestClient, officer_headers, drain):
    trace_id = _done_trace(client, officer_headers, drain)
    resp = client.get(
        f"/api/v1/trace/{trace_id}/report", params={"format": "pdf"}, headers=officer_headers
    )
    assert resp.status_code == 400
    assert "not implemented" in resp.json()["error"]["message"].lower()


def test_report_on_an_unfinished_trace_is_409(client: TestClient, officer_headers):
    trace_id = client.post(
        "/api/v1/trace", json={"address": SEED}, headers=officer_headers
    ).json()["trace_id"]  # queued, no drain
    resp = client.get(f"/api/v1/trace/{trace_id}/report", headers=officer_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "trace_not_ready"


def test_sahyog_notice_draft(client: TestClient, officer_headers, drain):
    trace_id = _done_trace(client, officer_headers, drain)
    resp = client.post(
        f"/api/v1/trace/{trace_id}/sahyog-notice",
        json={"vasp_rank": 1, "requesting_officer": "Insp. Priya K", "case_ref": "FIR 12/2026"},
        headers=officer_headers,
    )
    assert resp.status_code == 200
    draft = resp.json()["notice_draft"]
    assert "DemoExchange" in draft["to"]
    assert "FIR 12/2026" in draft["subject"]
    assert "preserve all records" in draft["body_markdown"]
    assert "Insp. Priya K" in draft["body_markdown"]
    assert draft["editable"] is True
    assert resp.json()["based_on"]["trace_id"] == trace_id


def test_sahyog_notice_bad_rank_is_400(client: TestClient, officer_headers, drain):
    trace_id = _done_trace(client, officer_headers, drain)
    resp = client.post(
        f"/api/v1/trace/{trace_id}/sahyog-notice", json={"vasp_rank": 9},
        headers=officer_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["details"]["available_ranks"] == [1]


def test_report_generation_is_audited(client: TestClient, officer_headers, admin_headers, drain):
    trace_id = _done_trace(client, officer_headers, drain)
    client.get(f"/api/v1/trace/{trace_id}/report", headers=officer_headers)
    audit = client.get("/api/v1/admin/audit", headers=admin_headers).json()
    assert "report.generate" in {e["action"] for e in audit["entries"]}
