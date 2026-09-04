# CLAUDE.md — operating manual for AI coding agents on Aegis

Read this and `MEMORY.md` before making changes. `MEMORY.md` tracks the *actual*
implementation state; this file is the *how we work* contract.

## What Aegis is

A real-time crypto-fraud attribution tool for cyber-crime investigators
(Smart India Hackathon 2026, PS **SIH26183**). Input: a victim-reported wallet
address (or raw complaint text). Output: a traced fund flow, detected laundering
typologies, an attributed exchange/VASP with a transparent confidence score, and
an evidence-grade report for the NCRP / SAHYOG workflow.

**It only reads public blockchain data and reports.** No smart contracts, no
wallet connections, no signing, no on-chain writes, no autonomous freezing. Do
not add any of these — they are out of scope by design.

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
frontend/   React 18 · Vite · TS · Tailwind.  Cytoscape graph + screens come later.
docs/       DATA_LICENSES.md, validation.md, SECURITY.md, PROVIDERS.md
scripts/    validate.sh — the single local gate
.github/    CI (path-filtered backend/frontend jobs + gitleaks)
```

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
- **Scope discipline.** Build the current phase only. Persistence, workers,
  streaming, and the AI models are later phases — do not pull them forward.

## Tech constraints

- Python **3.12** (pinned in `backend/.python-version` and CI). Managed by `uv`;
  `uv.lock` is committed.
- Node 20+; `package-lock.json` is committed; CI uses `npm ci`.
- Target architecture (later phases): Neo4j + PostgreSQL/pgvector + Redis/Celery +
  WebSocket. Not present yet — do not assume it in code.
