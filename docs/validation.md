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
Path filters skip the backend job for frontend-only changes and vice versa. A
`gitleaks` secret scan runs on every change regardless. `main` is protected: PRs
only, CI must be green, at least one review (configured in GitHub repo settings,
not in this repo).

## Known limits (Phase 0)

- No blockchain tracing engine, persistence, workers, or AI components yet — those
  are Phases 1+.
- The backend exposes only `GET /health`.
- The frontend is a placeholder shell.
