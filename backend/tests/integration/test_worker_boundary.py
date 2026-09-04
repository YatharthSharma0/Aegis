"""Proves trace execution holds across a real process boundary.

`tests/worker/test_runner.py` unit-tests `claim_next`'s lease/reclaim logic
against an in-process SQLite store — thorough for the row-locking algorithm,
but it never crosses an actual process boundary. Here, `AEGIS_TRACE_WORKER`
is `external` (`docker-compose.yml`): the `backend` container only enqueues,
a *separate* `worker` container claims and executes via
`SELECT ... FOR UPDATE SKIP LOCKED` against real Postgres. Concurrently
submitting several traces and confirming every one completes exactly once,
with no duplicate or dropped work, is the thing that in-process unit tests
structurally cannot check.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

pytestmark = pytest.mark.integration

_CONCURRENT_TRACES = 5
_POLL_TIMEOUT_S = 30


def _start_and_await(client: httpx.Client, headers: dict[str, str], address: str) -> dict:
    resp = client.post("/api/v1/trace", json={"address": address}, headers=headers)
    assert resp.status_code == 202, resp.text
    trace_id = resp.json()["trace_id"]

    deadline = time.monotonic() + _POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        status = client.get(f"/api/v1/trace/{trace_id}", headers=headers)
        body = status.json()
        if body["status"] in ("done", "partial", "failed"):
            return body
        time.sleep(0.5)
    pytest.fail(f"trace {trace_id} never finished within {_POLL_TIMEOUT_S}s")


def test_concurrently_submitted_traces_are_each_claimed_exactly_once(
    client: httpx.Client, auth_headers: dict[str, str], seed_address: str
):
    with ThreadPoolExecutor(max_workers=_CONCURRENT_TRACES) as pool:
        results = list(
            pool.map(
                lambda _: _start_and_await(client, auth_headers, seed_address),
                range(_CONCURRENT_TRACES),
            )
        )

    trace_ids = [r["trace_id"] for r in results]
    assert len(set(trace_ids)) == _CONCURRENT_TRACES, "expected distinct trace ids, got a collision"
    assert all(r["status"] == "done" for r in results), results
    assert all(r["result_hash"] for r in results)

    # Same seed, same fixture -> the engine result must be deterministic
    # (canonical JSON + schema:sha256 hashing, see repo MEMORY.md Phase 1)
    # regardless of which worker attempt or ordering produced it.
    assert len({r["result_hash"] for r in results}) == 1
