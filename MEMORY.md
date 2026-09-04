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
| Engine contract (Phase 1A) | `app/engine/` — **contract only, no live data fetching**. `canonical` (deterministic JSON + `schema:sha256` hashing, `SCHEMA_VERSION = aegis.engine.v1`); `errors` (exception taxonomy + `TrailLostReason`/`PartialReason` enums); `records` (provenance-preserving `ProviderSnapshot` / `NormalizedTransaction` / `Transfer` / `AddressActivity`, frozen pydantic, quantized decimals); `provider` (`ChainDataProvider` Protocol, read-only, returns data + snapshot); `result` (`Investigation` / `TraceResult` / `GraphNode` / `GraphEdge` / `VaspCandidate` / `ConfidenceTerms` / `TrailEvent`; `Investigation.result_hash()` excludes wall-clock timing). |
| Engine data replay (Phase 1B, part 1) | `app/engine/tron.py` (base58check Tron address validation, USDT-TRC20 constants); `app/engine/providers/fixture.py` — `FixtureProvider` replays a recorded fixture dir, verifies per-file sha256 against the manifest, re-derives `offset:` pagination, deterministic. `app/engine/fixtures/growjoy_tron_trc20/` — **synthetic** (`_build.py` regenerates it), a task-scam USDT flow: seed→rot1→rot2→cons→dep→exch_hot with a mixer peel and a rot3 fan-in. **No live TronGrid client yet** (real TRC-20 endpoint lacks per-record block height/hash — deferred pending a provenance-policy call). |
| Forward walk (Phase 1B, part 2) | `app/engine/walk.py` — `forward_trace(seed, chain, asset, provider, params, mixer_addresses, bridge_addresses)`. Two phases: BFS discovery (bounded by `max_hops` depth, `max_nodes`/`max_edges` budgets, wall-clock deadline; mixer/bridge nodes marked, not expanded) then haircut taint propagation in discovery-order (a DAG). Haircut ratio = `victim_taint_in / provider_total_in` so clean fan-in dilutes; each edge's taint ∝ its value; sum out ≤ sum in. Emits `TrailEvent`s (mixer/bridge/max_hops/min_value/min_taint/cycle), never a fabricated continuation. `python -m app.engine trace-fixture [--json]` runs it offline. |
| Account signals (Phase 1B, part 3) | `app/engine/signals.py` — `detect_account_signals([AddressStats]) -> SignalReport`. Behaviour heuristics for account chains (no CIOH): passthrough-rotation, peel-chain, rapid-fan-out, fan-in-consolidation (typologies) + deposit-fan-in, sweep-target, batch-withdrawals, high-activity-service (`vasp` kind, for 1C). Each hit carries `evidence` + `limitations`. Thresholds in `SignalConfig` (real-chain defaults; tests lower them). Wired into `forward_trace`: fills `TraceResult.typologies` + per-`GraphNode.typologies`. The `vasp`-kind hits are consumed by 1C attribution. 89 engine tests. |
| Frontend | Vite + React 18 + TS + Tailwind skeleton. Placeholder `App.tsx`. `eslint` (flat) + `tsc`/build + `vitest` configured. `/api` proxied to `:8000` in dev. |
| Containers | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (backend + frontend only). |
| Validation | `scripts/validate.sh` runs ruff/mypy/pytest + eslint/build/vitest. `pytest-timeout` (30s) so a stalled test fails loudly instead of hanging. |
| CI | `.github/workflows/ci.yml` — path-filtered backend/frontend jobs + `gitleaks` + `ci-ok` aggregation gate. |
| Docs | `docs/DATA_LICENSES.md` (stub), `docs/validation.md` (incl. branch-protection table + accepted deviation), `CLAUDE.md`, this file. |

## Not built yet (later phases — do not assume in code)

Live provider clients (TronGrid HTTP client is now Phase 4.5 in the vault plan;
no Ethereum — Phase 1D) · wallet clustering + VASP attribution + label packs +
the confidence formula (Phase 1C / Gate M2 — next) · GNN typology model · NLP
complaint extraction · grounded LLM report · PostgreSQL · Neo4j · Redis/Celery
workers · WebSocket streaming · auth · any real UI screen.

The engine `result` types are the frozen boundary the Phase 2 backend will
consume; do not change their shape without bumping `SCHEMA_VERSION`.

## Open Phase 0 items

- [x] Branch protection on `main` — applied 2026-09-04 by `YatharthSharma0` via
      `gh api`. Requires `ci-ok` (strict), PRs before merge, linear history, no
      force-push/deletion, **enforced for administrators**. Required approving
      reviews = **0** (accepted deviation: single contributor can't approve own
      PR; → 1 when collaborators join). Full table in `docs/validation.md`.
- [x] CI verified green on a real PR (#1).
- [ ] Fill `docs/DATA_LICENSES.md` rows as datasets are actually brought in.
- [ ] Replace the remaining 5 placeholder names/handles in `CONTRIBUTORS.md` with
      real members (Team Lead = Yatharth Sharma / `@YatharthSharma0` is filled;
      single real contributor so far).
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
- 2026-09-04 — Governance close-out: `enforce_admins` enabled; `docs/validation.md`
  corrected (had said "≥1 review") with a branch-protection table + the accepted
  0-review deviation documented; `pytest-timeout` added.
- 2026-09-04 — Phase 1A (engine contract): `app/engine/` — canonical
  serialization/hashing, error taxonomy, provenance-preserving normalized
  records, `ChainDataProvider` interface, trace-result boundary. 44 tests.
- 2026-09-04 — Phase 1B part 1 (data replay): Tron address validation +
  `FixtureProvider` (checksum-verified, deterministic, paginating) + the
  synthetic `growjoy_tron_trc20` fixture. Live TronGrid HTTP client deferred
  (per-record block height/hash gap).
- 2026-09-04 — Phase 1B part 2 (forward walk): `walk.forward_trace` — BFS
  discovery + haircut taint propagation over a discovery-order DAG, budgets +
  deadline + `TrailEvent`s, `Investigation` output with a stable `result_hash`.
  `python -m app.engine trace-fixture` CLI.
- 2026-09-04 — Phase 1B part 3 (account signals): `signals.detect_account_signals`
  — behaviour heuristics (rotation / peel / fan-in / fan-out + VASP-shape
  signals), each with evidence + limitations, wired into `forward_trace`
  (`TraceResult.typologies` + node labels). 89 engine tests. Next: 1C —
  attribution + label packs + confidence formula (Gate M2).
- 2026-09-04 — Vault: added `10-Execution-Plan/05a-Phase-4.5-Live-Provider-
  Integration.md` (live TronGrid, opt-in, post-M3, swap-in behind the frozen
  provider interface) per user request.
