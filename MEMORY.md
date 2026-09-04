# MEMORY.md — implementation state

The living record of what is *actually built* in this repository. Read it before
starting work; update it when you land a change that moves the state. Keep it
short and true. The design vault
(`~/Documents/Vaults/SIH26183-CryptoFraudTrace/`) remains the source of truth for
*design*; this file is the source of truth for *implementation*.

## Current state

- **Phase:** 0 — Foundation (in progress).
- **History:** an earlier "Aegis" showcase build existed and was discarded. This
  repo is a from-scratch rebuild started 2026-09-04. Ignore any external note
  describing a "working full-stack MVP" — it does not exist here.

## What exists

| Area | State |
|---|---|
| Repo hygiene | `.gitignore`, `.editorconfig`, `LICENSE` (MIT), `README.md`, `CONTRIBUTORS.md` |
| Backend | FastAPI skeleton, `GET /health` only. `uv` project, Python 3.12 pinned, `uv.lock` committed. `ruff` + `mypy` (strict) + `pytest` configured and green. Env via `app/config.py` + `.env.example`. |
| Frontend | Vite + React 18 + TS + Tailwind skeleton. Placeholder `App.tsx`. `eslint` (flat) + `tsc`/build + `vitest` configured. `/api` proxied to `:8000` in dev. |
| Containers | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (backend + frontend only). |
| Validation | `scripts/validate.sh` runs ruff/mypy/pytest + eslint/build/vitest. |
| CI | `.github/workflows/ci.yml` — path-filtered backend/frontend jobs + `gitleaks`. |
| Docs | `docs/DATA_LICENSES.md` (stub), `docs/validation.md`, `CLAUDE.md`, this file. |

## Not built yet (later phases — do not assume in code)

Blockchain tracing engine · wallet clustering · VASP attribution · GNN typology
model · NLP complaint extraction · grounded LLM report · PostgreSQL · Neo4j ·
Redis/Celery workers · WebSocket streaming · auth · any real UI screen.

## Open Phase 0 items

- [x] Branch protection on `main` — applied 2026-09-04 by `YatharthSharma0` (repo
      admin) via `gh api`. Requires the `ci-ok` status check (strict), PRs with 0
      required approvals (self-merge allowed until teammates join), linear
      history, no force-push, no deletion; admin bypass left on.
- [x] CI verified green on a real PR (this file's own PR).
- [ ] Fill `docs/DATA_LICENSES.md` rows as datasets are actually brought in.
- [ ] Replace placeholder names/handles in `CONTRIBUTORS.md` with real members.
- [ ] Raise `required_approving_review_count` to 1 once real collaborators join.

## Maintenance rule

When a PR changes the implementation state, update the tables above in the same
PR. One or two lines. Do not let this file drift from reality — future agents
trust it.

## Changelog

- 2026-09-04 — Repo re-initialised from scratch. Phase 0 scaffold: hygiene,
  backend + frontend skeletons, Docker/Compose, validate.sh, CI, docs.
- 2026-09-04 — `main` branch protection applied; CI (`ci-ok` gate) verified on a
  real PR. Phase 0 foundation complete bar the two follow-ups above.
