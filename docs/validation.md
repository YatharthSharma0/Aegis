# Validation

`./scripts/validate.sh` is the single local gate. It runs exactly what CI runs.
A change is not done until it passes.

```bash
./scripts/validate.sh            # backend + frontend
./scripts/validate.sh backend    # just the backend
./scripts/validate.sh frontend   # just the frontend
```

## What runs

| Area | Checks | Tooling |
|---|---|---|
| Backend | lint, type-check, tests, dependency scan, OpenAPI drift, migration up/down | `ruff check .`, `mypy app`, `pytest`, `pip-audit`, `alembic upgrade head / check / downgrade base / upgrade head` (via `uv run`) |
| Frontend | lint, type-check + build, tests, dependency scan, generated-types drift | `eslint .`, `tsc -b && vite build`, `vitest run`, `npm audit --omit=dev` |

See [`SECURITY.md`](SECURITY.md) for the full security checklist these dependency scans and auth/authz/rate-limit tests are evidence for.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — provisions Python 3.12 and backend deps
  (`uv sync --extra dev` in `backend/`).
- Node 20+ and `npm ci` in `frontend/`.

## Integration testing (Phase 4)

`./scripts/validate.sh` runs unit/component tests only — hermetic, no Docker
required, and that's deliberate (it's the fast gate every commit runs). A
separate suite proves the system works across real process/network
boundaries — engine -> backend -> a genuinely separate worker process ->
frontend — against a live `docker compose` stack:

```bash
docker compose up -d --wait
cd backend && uv run pytest tests/integration -m integration
```

`backend/tests/integration/` is excluded from the default `uv run pytest`
run (`addopts = -m "not integration"` in `pyproject.toml`) so it never blocks
`validate.sh` or CI; it must be run explicitly against a running stack. It
skips (not fails) with a clear message if the backend isn't reachable.

Covers: the full trace flow over HTTP (`test_happy_path.py`), auth/refresh
over the wire (`test_auth_flow.py`), rejected/failure states — unsupported
chain, malformed address, unknown trace id, reading a report before the
trace is done (`test_failure_paths.py`) — and concurrently submitted traces
each claimed exactly once by the separate `worker` container
(`test_worker_boundary.py`), which is the one guarantee an in-process unit
test structurally cannot check.

For a scripted manual demo run (not a test suite — human-readable PASS/FAIL
output), use the runbook:

```bash
./scripts/e2e_runbook.sh          # leaves the stack running afterward
./scripts/e2e_runbook.sh --down   # tears it down on exit
```

Not yet automated: a real worker-process-death mid-trace (lease-expiry
*recovery* is unit-tested in `backend/tests/worker/test_runner.py`; only the
claim-across-a-real-process-boundary half is covered here) and a
backend-down frontend banner check (`useHealth`) — both remain manual/visual
checks for now.

## CI

`.github/workflows/ci.yml` runs on every push to `main` and every pull request.
Path filters skip the backend job for frontend-only changes and vice versa; the
always-running `ci-ok` job aggregates their results into the single required
status check. A `gitleaks` secret scan runs on every change regardless.

## Branch protection on `main`

Configured in GitHub repo settings (not a repo file). Current state:

| Setting | Value | Notes |
|---|---|---|
| Require a pull request before merging | yes | no direct pushes |
| Required approving reviews | **0** | accepted deviation — see below |
| Require status checks (strict) | `ci-ok` | branch must be up to date |
| Dismiss stale approvals | yes | |
| Require linear history | yes | squash or rebase merges |
| Allow force pushes / deletions | no | |
| Enforce for administrators | yes | admins go through PRs too |

**Accepted deviation (2026-09-04):** the team's stated rule is ≥1 approving
review, but the repo currently has a single contributor who cannot approve their
own PR. Required approvals are set to **0** until real collaborators are added,
at which point this is raised to **1** (tracked in `MEMORY.md` open items and
`CONTRIBUTORS.md`).

## Known limits

- No live blockchain data by default — traces run against a recorded
  synthetic fixture unless `AEGIS_PROVIDER_MODE`/`AEGIS_TRONGRID_API_KEY`
  opt into live Tron mainnet (Phase 4.5, see `docs/PROVIDERS.md`). No
  live-recorded regression fixture exists yet — blocked on a real API key.
- No GNN typology model (Phase 1E), Ethereum adapter (Phase 1D), NLP
  complaint extraction (Phase 1F), or Neo4j graph store — none of these
  shipped; nothing in the product claims otherwise (see `docs/SECURITY.md`,
  "GNN eval reproducibility").
- No encryption-at-rest for complaint text — real (non-demo) complaint text
  is refused at the API boundary instead (see `docs/SECURITY.md`, DPDP row).
