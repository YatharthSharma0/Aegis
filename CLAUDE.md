# CLAUDE.md — operating manual for AI coding agents on Aegis

Read this and `MEMORY.md` before making changes. `MEMORY.md` tracks the *actual*
implementation state; this file is the *how we work* contract.

## What Aegis is

A crypto-fraud attribution tool for cyber-crime investigators. Input: a
victim-reported wallet address (or raw complaint text). Output: a traced fund
flow, detected laundering typologies, an attributed exchange/VASP with a
transparent confidence score, and an evidence-grade report — built with
India's NCRP/SAHYOG cybercrime-reporting workflow in mind, but the engine
itself isn't jurisdiction-specific. See `README.md` for the full "how it
works" explanation (forward-walk taint propagation, typology detection, the
VASP confidence formula) before touching the engine.

**It only reads public blockchain data and reports.** No smart contracts, no
wallet connections, no signing, no on-chain writes, no autonomous freezing. Do
not add any of these — they are out of scope by design.

This project originated as a Smart India Hackathon 2026 entry (PS SIH26183)
— that context still shapes some internal docs (the design vault's path,
NCRP/SAHYOG terminology) but `README.md` deliberately doesn't lead with it
for a general audience; don't reintroduce hackathon framing there without
being asked.

## Design source of truth

The system design lives in an Obsidian vault outside this repo
(`~/Documents/Vaults/SIH26183-CryptoFraudTrace/`). Architecture, feature scope,
the phased plan, and product decisions are defined there. This repo implements it.
When code and vault disagree, that is a flag to raise, not a silent choice.

The frontend's **visual design system** — the "forensic ledger" art direction,
color/typography/spacing tokens, component anatomy, and per-page layout — lives
in a separate vault: `~/Documents/Vaults/Aegis-Frontend-Blueprint/`. It governs
look and feel; it does not override the product/functional scope above (do not
pull forward WebSocket streaming, complaint-NLP extraction, clustering, or a
command palette just because that vault describes them — implement only what
the real backend supports, styled per that vault's tokens and components).

## Repository layout

```
backend/    Python 3.12 · FastAPI · uv.  Env vars read only in app/config.py.
  app/engine/     pure analytics engine (trace, signals, attribution, canonical hashing) — no I/O framework dependency
  app/api/        FastAPI routes
  app/domain/     cases, accounts, audit log, trace service
  app/worker/     the durable trace worker
  alembic/        migrations
frontend/   React 18 · Vite · TS · Tailwind · Cytoscape.js graph canvas · TanStack Query · Zustand
docs/       DATA_LICENSES.md, validation.md, SECURITY.md, PROVIDERS.md, DEPLOYMENT.md
scripts/    validate.sh — the single local gate; e2e_runbook.sh — scripted Docker Compose demo run
.github/    CI (path-filtered backend/frontend jobs + gitleaks)
```

See `README.md`'s "Repository layout" and "Architecture at a glance" for the
fuller version aimed at a first-time reader; this table is the quick
orientation for an agent already working in the code.

## Working rules

- **Validate before claiming done.** Run `./scripts/validate.sh` (or the relevant
  half) and confirm acceptance criteria. Generating code is not completing a task.
- **Conventional Commits**, small logical units: `type(scope): summary`
  (`feat fix refactor test docs chore perf build ci`). No "wip" blobs.
- **Branches:** `feature/<area>-<short-desc>`; small PRs. `main` is protected
  (PRs + green CI + review). During from-scratch scaffolding, small commits go
  direct to `main`; switch to the branch+PR flow once feature work starts.
- **Tests ship with the code.** Unit at minimum; integration where a change
  crosses a layer boundary. Include failure/misuse cases.
- **No secrets, ever.** `backend/.env.example` and `frontend/.env.example` are the
  only place config keys are declared. Add new keys there.
- **Types clean.** `mypy` strict on backend, `tsc` on frontend — no blanket
  ignores to silence real gaps.
- **Update docs** when interfaces, config, or architecture change — including
  `MEMORY.md` (see its maintenance rule) and `docs/`.
- **Scope discipline.** Persistence, auth, the durable worker, cases, and the
  frontend are all built (Phases 0–6 — see `MEMORY.md` for exact status per
  phase). What's still deliberately out: WebSocket live-hop streaming, a
  trained typology model (typology detection is rule-based by design, not a
  gap to fill with a GNN), NLP complaint extraction, demo-mode fixtures
  toggle, and a live-recorded TronGrid regression fixture (blocked on an API
  key — see `docs/PROVIDERS.md`). Don't pull these forward without checking
  `MEMORY.md` first.

## Tech constraints

- Python **3.12** (pinned in `backend/.python-version` and CI). Managed by `uv`;
  `uv.lock` is committed.
- Node 20+; `package-lock.json` is committed; CI uses `npm ci`.
- Persistence is **PostgreSQL** (Docker Compose / deployed) or **SQLite**
  (local dev default) via SQLAlchemy 2.0 + Alembic — present now, not a later
  phase. No Neo4j, no Redis/Celery — earlier planning docs mentioned these;
  none were adopted, and code should not assume them. The durable trace queue
  is a Postgres table with row-level locking (`SELECT ... FOR UPDATE SKIP
  LOCKED`), not a separate broker. WebSocket live-hop streaming is still
  genuinely deferred (P2) — polling is the current source of truth.
