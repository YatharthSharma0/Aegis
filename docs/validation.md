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
| Backend | lint, type-check, tests | `ruff check .`, `mypy app`, `pytest` (via `uv run`) |
| Frontend | lint, type-check + build, tests | `eslint .`, `tsc -b && vite build`, `vitest run` |

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — provisions Python 3.12 and backend deps
  (`uv sync --extra dev` in `backend/`).
- Node 20+ and `npm ci` in `frontend/`.

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

## Known limits (Phase 0)

- No blockchain tracing engine, persistence, workers, or AI components yet — those
  are Phases 1+.
- The backend exposes only `GET /health`.
- The frontend is a placeholder shell.
