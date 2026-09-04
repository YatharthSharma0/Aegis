"""Failure states that must render honestly, not silently succeed or hang.

Covers Phase 4's scoped failure paths: an unsupported chain/address, and a
not-yet-finished trace read (the `TraceNotReadyError` a client hits if it
requests a report before polling reports `done`/`partial`). Worker-death /
lease-expiry recovery is unit-tested against real Postgres semantics in
`tests/worker/test_runner.py`; `test_worker_boundary.py` in this suite
additionally proves it holds when the claimer is a genuinely separate
process (the Compose `worker` service), not just a thread in-process.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


def test_unsupported_chain_is_rejected(client: httpx.Client, auth_headers: dict[str, str]):
    resp = client.post(
        "/api/v1/trace",
        json={"address": "0x0000000000000000000000000000000000dEaD", "chain": "ethereum"},
        headers=auth_headers,
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()["error"]
    assert body["code"] == "invalid_request"
    assert "tron" in str(body["details"]).lower() or "supported" in body["message"].lower()


def test_malformed_address_is_rejected(client: httpx.Client, auth_headers: dict[str, str]):
    resp = client.post(
        "/api/v1/trace", json={"address": "not-a-real-address"}, headers=auth_headers
    )
    assert resp.status_code == 400, resp.text


def test_unknown_trace_id_is_a_404(client: httpx.Client, auth_headers: dict[str, str]):
    resp = client.get("/api/v1/trace/does-not-exist", headers=auth_headers)
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "not_found"


def test_report_for_an_unfinished_trace_is_honest_not_a_stale_result(
    client: httpx.Client, auth_headers: dict[str, str], seed_address: str
):
    """A report requested in the instant right after submission (before the
    worker has claimed the row) must reflect that the trace isn't done —
    never a cached/blank result presented as final."""
    start = client.post(
        "/api/v1/trace", json={"address": seed_address}, headers=auth_headers
    )
    trace_id = start.json()["trace_id"]

    status = client.get(f"/api/v1/trace/{trace_id}", headers=auth_headers)
    body = status.json()
    if body["status"] in ("queued", "running"):
        assert body["result"] is None
        assert body["result_hash"] is None

        report = client.get(f"/api/v1/trace/{trace_id}/report", headers=auth_headers)
        assert report.status_code == 409, report.text
        assert report.json()["error"]["code"] == "trace_not_ready"
