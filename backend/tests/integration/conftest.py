"""Fixtures for the integration suite (Phase 4).

Unlike the rest of `tests/`, these hit a *real* running stack over HTTP —
they exercise the process/network boundaries a `TestClient` unit test can't:
the external worker container claiming rows over real Postgres row locks,
CORS/auth headers on the wire, the backend's actual `uvicorn` process.

Bring the stack up first:

    docker compose up -d --wait

Then run just this suite:

    cd backend && uv run pytest tests/integration -m integration

`AEGIS_E2E_BASE_URL` overrides the backend origin (default matches
`docker-compose.yml`'s published port). All fixtures skip the suite with a
clear reason if the backend isn't reachable, so accidentally running
`uv run pytest` without the stack up fails fast and obviously rather than
hanging.
"""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from collections.abc import Iterator

import httpx
import pytest

BASE_URL = os.environ.get("AEGIS_E2E_BASE_URL", "http://localhost:8000")
_HEALTH_TIMEOUT_S = 30
_TEST_PASSWORD = "integration-test-password-not-for-prod"


def _compose_exec(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a command inside the `backend` compose service.

    Requires the `docker compose` CLI and a running stack — the same
    precondition every fixture here already enforces.
    """
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    """Wait for the backend to answer `/api/v1/health`, or skip the suite."""
    deadline = time.monotonic() + _HEALTH_TIMEOUT_S
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{BASE_URL}/api/v1/health", timeout=2)
            if resp.status_code == 200:
                return BASE_URL
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(1)
    pytest.skip(
        f"backend not reachable at {BASE_URL} after {_HEALTH_TIMEOUT_S}s "
        f"(run `docker compose up -d --wait` first): {last_error}"
    )


@pytest.fixture(scope="session")
def client(base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=base_url, timeout=10) as c:
        yield c


@pytest.fixture(scope="session")
def test_user(base_url: str) -> tuple[str, str]:
    """A known officer account in the Compose stack's database, created
    idempotently via the admin-only `create_user.py` script (there is no
    signup endpoint — see repo `MEMORY.md`, "Signing in").
    """
    email = "integration-tests@aegis.local"
    result = _compose_exec(
        "uv", "run", "python", "scripts/create_user.py",
        "--email", email, "--name", "Integration Tests",
        "--role", "officer", "--password", _TEST_PASSWORD,
    )
    stderr_lower = result.stderr.lower()
    if result.returncode != 0 and "unique" not in stderr_lower and "already" not in stderr_lower:
        pytest.fail(
            f"could not provision the integration test user via `docker compose exec`: "
            f"{result.stderr or result.stdout}"
        )
    return email, _TEST_PASSWORD


@pytest.fixture
def auth_headers(client: httpx.Client, test_user: tuple[str, str]) -> dict[str, str]:
    email, password = test_user
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_address() -> str:
    """A valid address in the `growjoy_tron_trc20` fixture the compose
    backend is configured to run against (`AEGIS_FIXTURE_ID`, see
    `backend/.env.example`); mirrors the SEED constant used by the worker's
    own unit tests (`tests/worker/test_runner.py`).
    """
    return "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


@pytest.fixture
def unique_case_ref() -> str:
    return f"integration-{uuid.uuid4().hex[:8]}"
