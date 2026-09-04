"""The rehearsed demo path, scripted: address in -> traced flow, typologies,
attributed VASP, evidence-grade report out. Exercises the real boundary the
unit suites can't: HTTP -> Postgres-backed queue -> a separate `worker`
container claiming and executing the row -> HTTP again.
"""

from __future__ import annotations

import time

import httpx
import pytest

pytestmark = pytest.mark.integration

_POLL_TIMEOUT_S = 20
_TERMINAL = {"done", "partial", "failed"}


def _poll_until_terminal(client: httpx.Client, headers: dict[str, str], trace_id: str) -> dict:
    deadline = time.monotonic() + _POLL_TIMEOUT_S
    last: dict = {}
    while time.monotonic() < deadline:
        resp = client.get(f"/api/v1/trace/{trace_id}", headers=headers)
        assert resp.status_code == 200, resp.text
        last = resp.json()
        if last["status"] in _TERMINAL:
            return last
        time.sleep(0.5)
    pytest.fail(
        f"trace {trace_id} did not reach a terminal state within {_POLL_TIMEOUT_S}s: {last}"
    )


def test_full_investigation_flow(
    client: httpx.Client, auth_headers: dict[str, str], seed_address: str
):
    start = client.post(
        "/api/v1/trace", json={"address": seed_address}, headers=auth_headers
    )
    assert start.status_code == 202, start.text
    accepted = start.json()
    assert accepted["status"] == "queued"
    trace_id = accepted["trace_id"]

    final = _poll_until_terminal(client, auth_headers, trace_id)
    assert final["status"] == "done", final
    assert final["result"] is not None
    assert final["result_hash"]
    assert final["started_at"] is not None
    assert final["finished_at"] is not None

    graph = client.get(f"/api/v1/trace/{trace_id}/graph", headers=auth_headers)
    assert graph.status_code == 200, graph.text
    graph_body = graph.json()
    assert graph_body["nodes"], "expected at least the seed node in the graph"

    report = client.get(f"/api/v1/trace/{trace_id}/report", headers=auth_headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["header"]["result_hash"] == final["result_hash"]


def test_report_reflects_the_same_trace_across_repeated_reads(
    client: httpx.Client, auth_headers: dict[str, str], seed_address: str
):
    """A second read must be idempotent — evidentiary reports can't drift
    between requests (an investigator may pull the same report twice)."""
    start = client.post(
        "/api/v1/trace", json={"address": seed_address}, headers=auth_headers
    )
    trace_id = start.json()["trace_id"]
    _poll_until_terminal(client, auth_headers, trace_id)

    first = client.get(f"/api/v1/trace/{trace_id}/report", headers=auth_headers)
    second = client.get(f"/api/v1/trace/{trace_id}/report", headers=auth_headers)
    assert first.json()["header"]["result_hash"] == second.json()["header"]["result_hash"]
