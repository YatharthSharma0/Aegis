# Aegis

**Trace crypto fraud from a victim's wallet address to the exchange that received it — with the evidence to prove it.**

Aegis takes a scam victim's wallet address, follows the funds forward on the
public blockchain, and produces an evidence-grade report: the traced fund
flow, the laundering techniques it passed through, and the exchange (VASP)
that likely received it — with a transparent, arithmetic confidence score,
not a black-box guess.

> **Assistive, not autonomous.** Aegis produces leads for a human investigator
> to review, not automated action. It only *reads* public blockchain data and
> *reports* — no wallet connections, no transaction signing, no on-chain
> writes, and no ability to freeze or move funds.

---

## Table of contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
  - [1. The trace — forward walk with haircut taint propagation](#1-the-trace--forward-walk-with-haircut-taint-propagation)
  - [2. Typology detection](#2-typology-detection)
  - [3. VASP attribution](#3-vasp-attribution)
  - [4. Reproducibility](#4-reproducibility)
  - [5. Chain data — fixture vs. live](#5-chain-data--fixture-vs-live)
  - [6. Backend](#6-backend)
  - [7. Frontend](#7-frontend)
- [Architecture at a glance](#architecture-at-a-glance)
- [Installing and running it](#installing-and-running-it)
  - [Option A — Docker Compose (fastest)](#option-a--docker-compose-fastest)
  - [Option B — run backend and frontend directly](#option-b--run-backend-and-frontend-directly)
  - [Creating a login](#creating-a-login)
  - [Running a trace](#running-a-trace)
  - [Tracing live blockchain data (optional)](#tracing-live-blockchain-data-optional)
- [Repository layout](#repository-layout)
- [Validation, tests, and CI](#validation-tests-and-ci)
- [Deployment](#deployment)
- [Security](#security)
- [Contributing](#contributing)
- [Licence](#licence)

---

## What it does

An investigator submits a wallet address. Aegis:

1. **Traces the funds forward**, hop by hop, on the public blockchain — rendered as an interactive graph, not just a table.
2. **Propagates taint through the flow** using a haircut model, so it can say *how much* of what reached each downstream address actually came from the victim, not just *that* a path exists.
3. **Detects laundering typologies** along the way — peel chains, wallet rotation, fan-in/fan-out patterns, mixer and bridge hops — and marks honestly where a trail goes cold instead of inventing a continuation.
4. **Attributes the likely receiving exchange (VASP)**, either from a confirmed label dataset or from behavioral heuristics, with a confidence score built from named, weighted terms you can see the arithmetic for.
5. **Generates an evidence-grade report** — a content-addressed result hash, per-claim provenance, and an editable notice draft — suitable for a real investigative workflow (built with India's NCRP/SAHYOG cybercrime-reporting process in mind, but the underlying engine isn't jurisdiction-specific).

## How it works

### 1. The trace — forward walk with haircut taint propagation

The core is a pure analytics engine (`backend/app/engine/`, no I/O framework
dependency) that runs a two-phase forward walk from the seed address:

1. **Discovery** — breadth-first outward from the seed along outgoing
   transfers, bounded by a hop limit, node/edge budgets, and a wall-clock
   deadline. Every provider response consulted along the way is recorded as
   an immutable, checksummed `ProviderSnapshot` — every downstream claim can
   be traced back to the exact API response it came from.
2. **Propagation** — the discovered graph (restricted to discovery-order
   edges, which makes it a DAG) is walked in topological order. Each
   address's **haircut ratio** is `victim_taint_in / total_in`, using the
   provider-reported total inflow — so clean money mixing in at a hub
   correctly dilutes the victim's fraction, and the taint handed out on any
   edge never exceeds what came in. This is what lets Aegis say "38% of the
   funds reaching this address trace back to the victim" instead of a bare
   yes/no.

Where a branch legitimately can't continue — it hit a mixer, a bridge, the
hop limit, a rate limit — that's recorded as a **typed trail-lost reason**,
not silently dropped or faked as a dead end.

### 2. Typology detection

Structural heuristics over the discovered graph (`app/engine/signals.py`)
flag known laundering patterns: **peel chains** (a dominant output plus a
small peeled-off remainder, repeated), **wallet rotation** (funds passed
through in full, hop after hop), **fan-in**/**fan-out** at exchange-shaped
degree, and mixer/bridge detection that stops expansion rather than guessing
what's on the other side.

### 3. VASP attribution

Two-tier attribution, always honest about which tier it's in:

- **Dataset-confirmed** — the reached address matches a loaded label
  (`app/engine/labels.py`): a real exchange name, high confidence.
- **Heuristic** — no label, but the address *behaves* like an exchange
  deposit/hot wallet (fan-in shape, fast forwarding). Named "unidentified
  VASP-like endpoint," never given a fabricated name.
- **Conflict** — two labels disagree. Both are surfaced; Aegis never
  silently picks one.

The confidence score is transparent arithmetic, not a black box:

```
confidence = w1·source_score + w2·path_directness + w3·taint_retained
           + w4·corroboration − p1·mixer_on_path − p2·bridge_uncertainty
           (clamped to [0, 1])
```

with default weights `w1=0.45, w2=0.15, w3=0.20, w4=0.20, p1=0.25, p2=0.10`
(`app/engine/attribution.py`). Every term is carried through to the report
so it can print the actual arithmetic behind a given score, not just the
final number.

### 4. Reproducibility

Every result is deterministically hashed: canonical JSON serialization with
strict rules (sorted keys, fixed-point decimals, no floats, UTC timestamps)
feeds a `schema_version:sha256` hash (`app/engine/canonical.py`). The same
cached input always produces the same result hash — an investigator (or a
court) can verify a report wasn't altered after the fact.

### 5. Chain data — fixture vs. live

The engine talks to chain data through one frozen interface
(`ChainDataProvider`), with two implementations:

- **`FixtureProvider`** (default everywhere, including CI and the offline
  demo) — replays a recorded, checksummed fixture directory. Fully
  deterministic, zero network calls, zero external dependency.
- **`TronGridProvider`** (opt-in) — live Tron mainnet via
  [TronGrid](https://www.trongrid.io/), with retry-with-backoff on
  rate limits/timeouts/5xx, an on-disk response cache, and key hygiene (the
  API key is never logged, cached, or embedded in provenance). See
  [`docs/PROVIDERS.md`](docs/PROVIDERS.md) for the full design, including a
  real gap TronGrid's API has (no block number/hash on its transfer-list
  endpoint) and how Aegis resolves it without touching the engine.

Selecting between them is one config value (`AEGIS_PROVIDER_MODE`) — nothing
downstream of the provider interface knows or cares which one it's talking to.

### 6. Backend

FastAPI (Python 3.12, managed by [`uv`](https://docs.astral.sh/uv/)), with:

- **JWT auth** (HS256), rotating refresh tokens (old token burned on
  rotation), role-gated admin routes.
- **A hash-chained, append-only audit log** — every trace start/read, report
  generation, and login is recorded as `row_hash =
  sha256(canonical_json({"prev": ..., "fields": ...}))`; tampering with any
  row is detectable by re-walking the chain.
- **A durable trace worker**, not fire-and-forget background tasks — a SQL
  row-locking queue (`SELECT ... FOR UPDATE SKIP LOCKED` on Postgres) with
  lease expiry and retry, so a crashed worker's in-flight trace gets
  reclaimed rather than lost. Runs either inline (dev) or as a separate
  process (`python -m app.worker`, the Compose/production shape).
- **Case management** — cases and complaints, with real (non-demo)
  complaint text refused at the API boundary until encryption-at-rest and a
  retention policy exist (see [`docs/SECURITY.md`](docs/SECURITY.md)) —
  enforced server-side, not just documented.
- **In-process rate limiting** on login and trace-start, with a proper `429`
  + `Retry-After`, tuned so a judge/demo re-run doesn't get walled off by
  abuse-prevention limits meant for actual abuse.
- **Evidence-grade report generation** plus an editable notice-draft
  endpoint, both built from the same hashed `Investigation` the trace
  produced.

### 7. Frontend

React 18 + Vite + TypeScript + Tailwind, with:

- **Cytoscape.js** for the interactive fund-flow graph — click a node or a
  transfers-table row to select it, filter by minimum value, isolate a
  path, switch layouts.
- **Types generated from the backend's OpenAPI schema**
  (`openapi-typescript`), checked in CI for drift — the frontend can't
  silently go stale against the API contract.
- Risk and confidence are **never colour-only** — always colour + icon +
  label, and fraud risk and attribution confidence are kept as visually
  distinct concepts (a "confident" attribution isn't the same claim as a
  "high-risk" one).
- Day/night theme, keyboard-accessible fallback table for the graph, a
  backend-unavailable banner, and honest empty/error states throughout
  (never a fabricated result standing in for "still loading" or "failed").

## Architecture at a glance

| Layer | Stack |
|---|---|
| Analytics engine | Pure Python, no I/O framework — deterministic, independently testable |
| Backend | FastAPI · SQLAlchemy 2.0 + Alembic · JWT auth · `uv` |
| Persistence | PostgreSQL (Docker Compose / deployed) or SQLite (local dev default) |
| Frontend | React 18 · Vite · TypeScript · Tailwind · Cytoscape.js · TanStack Query · Zustand |
| Chain data | Recorded fixture (default) or live TronGrid (opt-in) behind one frozen interface |

No Neo4j, no Celery/Redis, no GraphSAGE GNN — earlier plans mentioned these;
none were adopted. The graph is rendered client-side from the trace result,
the durable queue is a Postgres table (not a separate broker), and typology
detection is rule-based, not a trained model — all deliberate scope calls to
keep the system's actual behavior fully explainable, not because a model
would be strictly worse.

## Installing and running it

Prerequisites: [`uv`](https://docs.astral.sh/uv/) (manages Python 3.12), Node 20+, and either Docker with Compose *or* nothing else if you run backend/frontend directly.

### Option A — Docker Compose (fastest)

```bash
git clone https://github.com/YatharthSharma0/Aegis.git
cd Aegis
docker compose up --build
```

This starts Postgres, the backend API, a separate worker process, and the
frontend dev server together, wired to talk to each other. Frontend at
`http://localhost:5173`, backend at `http://localhost:8000` (`/docs` for the
interactive OpenAPI UI).

### Option B — run backend and frontend directly

```bash
# Backend
cd backend
uv sync                                # creates .venv with Python 3.12 + deps
uv run uvicorn app.main:app --reload   # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

No `.env` file is required to start — `backend/.env.example`'s defaults are
sufficient for local dev (SQLite, the recorded fixture, an inline worker
thread). Copy it to `backend/.env` if you want to override anything.

### Creating a login

There's no public signup — this is an investigator-facing tool, so accounts
are created via an admin-only script:

```bash
cd backend
uv run python scripts/create_user.py \
  --email you@example.com --name "Your Name" --role officer --password 'yourpassword'
```

`--role` is one of `officer`, `analyst`, `admin` (only `admin` sees the audit-log screen). Then sign in at the frontend with that email/password.

### Running a trace

Sign in, go to **New trace**, and submit the fixture's known seed address:

```
TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC
```

against the default `growjoy_tron_trc20` fixture (a synthetic but
realistic USDT-TRC20 fund flow through a peel chain to a labeled exchange
deposit address). You'll get a real traced graph, typology flags, and a
VASP attribution with full confidence arithmetic — entirely offline.

You can also run a trace from the command line, no backend/frontend needed:

```bash
cd backend
uv run python -m app.engine trace-fixture
```

### Tracing live blockchain data (optional)

By default every trace — including the ones above — runs against the
recorded fixture, not live chain data. To trace real Tron mainnet:

1. Get a free API key from [trongrid.io](https://www.trongrid.io/).
2. In `backend/.env`, set `AEGIS_TRONGRID_API_KEY=<your key>` and
   `AEGIS_PROVIDER_MODE=auto` (live iff the key is present, fixture
   otherwise) or `live` (always live).

See [`docs/PROVIDERS.md`](docs/PROVIDERS.md) for how live mode works, its
retry/caching behavior, and current known limitations.

## Repository layout

```
backend/    FastAPI app — engine, API routes, auth, worker, migrations, tests
  app/engine/       the pure analytics engine (trace, signals, attribution, canonical hashing)
  app/api/          FastAPI routes
  app/domain/       cases, accounts, audit log, trace service
  app/worker/       the durable trace worker
  alembic/          migrations
  tests/            unit + component tests; tests/integration/ needs Docker Compose
frontend/   React + Vite + TypeScript app
  src/pages/        screens (dashboard, cases, trace, report, admin audit)
  src/components/   the graph canvas and shared UI
  src/api/          typed API client (generated types + hand-written client)
docs/       PROVIDERS.md, SECURITY.md, DEPLOYMENT.md, DATA_LICENSES.md, validation.md
scripts/    validate.sh (the single local check gate), e2e_runbook.sh (scripted demo run)
.github/    CI (lint/type-check/test/dependency-scan/secret-scan, path-filtered)
CLAUDE.md   Operating manual for AI coding agents working in this repo
MEMORY.md   Living record of actual implementation state, phase by phase
```

## Validation, tests, and CI

```bash
./scripts/validate.sh            # everything CI runs: lint, type-check, tests, dependency scan, drift checks
./scripts/validate.sh backend    # just the backend
./scripts/validate.sh frontend   # just the frontend
```

Backend: `ruff`, `mypy` (strict), `pytest` (220+ tests), `pip-audit`, OpenAPI-drift
check, Alembic migration up/down. Frontend: `eslint`, `tsc` + `vite build`,
`vitest` (30+ tests), `npm audit`, generated-types drift check.

A separate Docker-Compose-backed integration suite
(`backend/tests/integration/`, run explicitly — see
[`docs/validation.md`](docs/validation.md)) proves the system works across
real process boundaries: a genuinely separate worker process claiming rows
over real Postgres locks, not just an in-process thread.

## Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the staging deployment
topology (Vercel + Railway), environment variable names, and known gaps —
written plainly, including what isn't finished yet.

## Security

Read [`docs/SECURITY.md`](docs/SECURITY.md) for the evidence-based security
checklist (dependency scanning, secret scanning, auth/authz, rate limiting,
DPDP-style handling of complaint text) and its explicitly-scoped limits —
this is engineering-level verification, not a professional third-party audit.

## Contributing

See [`CONTRIBUTORS.md`](CONTRIBUTORS.md). Conventional Commits, small logical
units, `main` is protected (PRs + green CI). Never commit secrets —
`.env.example` files are the single source of truth for configuration names.

## Licence

[MIT](LICENSE). Third-party dataset and label-set licences are tracked in
[`docs/DATA_LICENSES.md`](docs/DATA_LICENSES.md).
