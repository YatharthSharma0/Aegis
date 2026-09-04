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
| Backend | FastAPI. `uv` project, Python 3.12 pinned. Env via `app/config.py` + `.env.example`. **Trace API (Phase 2, PR #9)**: `POST /api/v1/trace` → 202 `{trace_id,status,stream_url}`; `GET /api/v1/trace/{id}` (polling — status + result + `result_hash`); `GET /api/v1/trace/{id}/graph` (nodes/edges). Layering: `app/api/` (routes + error envelope) → `app/domain/` (`TraceService`, `InvestigationStore` Protocol) → `app/engine_bridge.py` (only place the backend calls `app.engine`) → Phase 1 `forward_trace`. Runs on `BackgroundTasks` (labelled single-process demo fallback — durable worker is a later PR). No auth / audit-log / cases yet. `backend/openapi.json` committed + CI-checked. |
| Persistence (Phase 2, PR #10) | SQLAlchemy 2.0 + Alembic. `app/db/` (`Base`, `TraceRun` model, engine/session factory). `SqlInvestigationStore` implements `InvestigationStore` (stores the full engine `Investigation` as JSON + `result_hash`); `get_trace_service` now uses it. `AEGIS_DATABASE_URL` (SQLite local default, Postgres via Compose). Migrations `alembic/versions/000N_*.py`; `alembic check` runs in CI + `validate.sh` (schema-drift guard). Container entrypoint runs `alembic upgrade head`; non-prod `lifespan` runs `create_all()`. Compose gains a `db` (postgres:16) service. Tests use a throwaway SQLite DB (`tests/conftest.py`). `InMemoryInvestigationStore` kept for unit tests. |
| Auth (Phase 2, PR #11) | JWT (PyJWT HS256) + argon2 passwords. `app/security/` (`passwords.py`, `tokens.py` — access carries `sub`+`role`, refresh carries `sub`+`jti`, `type` claim prevents cross-use). `app/domain/accounts.py` (`Role` enum, `Account`, `AccountService`: authenticate / issue / **rotate refresh** — old jti burned, reuse → 401) + `SqlAccountStore` (`users`, `refresh_tokens` tables, migration 0002). `POST /api/v1/auth/login` / `/refresh` / `GET /auth/me` (public except `/me`). Trace router now `dependencies=[Depends(get_current_user)]` → 401 without a token; `require_role(...)` / `require_admin` for `/admin/*`. `AEGIS_JWT_SECRET` (+ TTLs); prod refuses the dev default. `scripts/create_user.py` (no public signup). |
| Audit log (Phase 2, PR #12) | Hash-chained append-only `audit_log` (migration 0003). `app/security/audit.py` — `row_hash = sha256(canonical_json({"prev": prev_row_hash, "fields": <fixed content columns>}))`, genesis = 64 zeros. `app/domain/audit.py` — `AuditService.record(action, actor=…, …)` (append is atomic: read-prev + insert in one txn, PG advisory lock), `verify() -> AuditVerification` (detects mutation / deletion / insertion / reorder, reports `broken_at_seq`). `SqlAuditStore`. Trace routes now log `trace.start` / `trace.complete` / `trace.failed` / `trace.read` / `trace.read_graph` with actor + request id. `RequestIdMiddleware` (`X-Request-ID` in/out, on `request.state`). `GET /api/v1/admin/audit` (`require_admin`) → `{verification, entries}`. Tamper-detection test uses raw SQL UPDATE/DELETE/INSERT. |
| Durable worker (Phase 2, PR #13) | `BackgroundTasks` **removed**. `trace_runs` gains `attempts`/`worker_id`/`lease_expires_at` (migration 0004). `InvestigationStore.claim_next(worker_id, lease_s)` — atomically moves the oldest `queued` (or lease-expired `running`) row to `running` with a fresh lease (PG `SELECT … FOR UPDATE SKIP LOCKED`; SQLite single-writer). `app/worker/` — `TraceWorker.run_once()` / `run_forever(stop)` (claim → `TraceService.execute` → persist → audit `trace.claimed`/`trace.complete`/`trace.failed`); over `worker_max_attempts` → `failed`, not retried. `AEGIS_TRACE_WORKER=inline` (lifespan daemon thread — dev default) \| `external` (`python -m app.worker`; Compose `worker` service, `AEGIS_SKIP_MIGRATIONS=1`). `POST /trace` just queues + audits `trace.start`. `TraceService.run_next()` for the inline/test path. 170 tests (lease recovery, give-up, oldest-first, no-steal, `run_forever`). |
| Case management (Phase 2, PR #14) | `cases` + `complaints` tables (migration 0005). `app/domain/cases.py` (`CaseStatus`/`ComplaintSource` enums, `Case`/`Complaint`, `CaseService`) + `SqlCaseStore`. `POST /api/v1/cases` (201; unique `ref_no` -> 409), `GET /api/v1/cases` (filter `status`, `mine`), `GET /api/v1/cases/{id}` (case + complaint previews + its trace-run summaries via `InvestigationStore.list_by_case`), `PATCH /api/v1/cases/{id}`, `POST /api/v1/cases/{id}/complaints`. `POST /trace` with a `case_id` now 404s if the case is unknown. Real (`is_demo=false`) complaint text is **refused** (encryption/retention pending, DPDP). Audit: `case.create`/`case.update`/`complaint.attach`. Errors refactored to `NotFoundError`/`InvalidRequestError`/`ConflictError` base classes. 183 tests. |
| Report + SAHYOG notice (Phase 2, PR #15) | `app/domain/reports.py` — `build_report(record, generated_by)` renders a finished `Investigation` into a structured JSON report (header + `result_hash`, officer summary, VASP candidates **with the confidence formula spelled out**, fund-flow evidence table, typologies, trail events, cited provider snapshots, and a **Bharatiya Sakshya Adhiniyam s.63 certification block** whose reproducibility anchor is the result hash). `build_sahyog_notice(record, vasp_rank, …)` templates a preservation-request notice draft (`editable: true`). `GET /api/v1/trace/{id}/report?format=json` (pdf -> 400 not-implemented; unfinished trace -> 409) + `POST /api/v1/trace/{id}/sahyog-notice`. Audit: `report.generate` / `notice.draft`. 190 tests. |
| Engine contract (Phase 1A) | `app/engine/` — **contract only, no live data fetching**. `canonical` (deterministic JSON + `schema:sha256` hashing, `SCHEMA_VERSION = aegis.engine.v1`); `errors` (exception taxonomy + `TrailLostReason`/`PartialReason` enums); `records` (provenance-preserving `ProviderSnapshot` / `NormalizedTransaction` / `Transfer` / `AddressActivity`, frozen pydantic, quantized decimals); `provider` (`ChainDataProvider` Protocol, read-only, returns data + snapshot); `result` (`Investigation` / `TraceResult` / `GraphNode` / `GraphEdge` / `VaspCandidate` / `ConfidenceTerms` / `TrailEvent`; `Investigation.result_hash()` excludes wall-clock timing). |
| Engine data replay (Phase 1B, part 1) | `app/engine/tron.py` (base58check Tron address validation, USDT-TRC20 constants); `app/engine/providers/fixture.py` — `FixtureProvider` replays a recorded fixture dir, verifies per-file sha256 against the manifest, re-derives `offset:` pagination, deterministic. `app/engine/fixtures/growjoy_tron_trc20/` — **synthetic** (`_build.py` regenerates it), a task-scam USDT flow: seed→rot1→rot2→cons→dep→exch_hot with a mixer peel and a rot3 fan-in. **No live TronGrid client yet** (real TRC-20 endpoint lacks per-record block height/hash — deferred pending a provenance-policy call). |
| Forward walk (Phase 1B, part 2) | `app/engine/walk.py` — `forward_trace(seed, chain, asset, provider, params, mixer_addresses, bridge_addresses)`. Two phases: BFS discovery (bounded by `max_hops` depth, `max_nodes`/`max_edges` budgets, wall-clock deadline; mixer/bridge nodes marked, not expanded) then haircut taint propagation in discovery-order (a DAG). Haircut ratio = `victim_taint_in / provider_total_in` so clean fan-in dilutes; each edge's taint ∝ its value; sum out ≤ sum in. Emits `TrailEvent`s (mixer/bridge/max_hops/min_value/min_taint/cycle), never a fabricated continuation. `python -m app.engine trace-fixture [--json]` runs it offline. |
| Account signals (Phase 1B, part 3) | `app/engine/signals.py` — `detect_account_signals([AddressStats]) -> SignalReport`. Behaviour heuristics for account chains (no CIOH): passthrough-rotation, peel-chain, rapid-fan-out, fan-in-consolidation (typologies) + deposit-fan-in, sweep-target, batch-withdrawals, high-activity-service (`vasp` kind, for 1C). Each hit carries `evidence` + `limitations`. Thresholds in `SignalConfig`. Wired into `forward_trace`: fills `TraceResult.typologies` + per-`GraphNode.typologies`. |
| Attribution (Phase 1C — Gate M2) | `app/engine/labels.py` (`LabelPack`/`LabelSet`: versioned, checksum-verified; `LabelType` keeps `vasp`/`service` distinct from `sanctions`/`mixer`/`bridge`) + `app/engine/attribution.py` (`attribute([EndpointContext], LabelSet) -> tuple[VaspCandidate]`). Two-tier: dataset-confirmed (exact / via-cluster) vs heuristic ("Unidentified VASP-like endpoint", name stays None) vs conflict (never silently picks) vs unknown sink. Transparent confidence = `w1·source + w2·directness + w3·taint_retained + w4·corroboration − p1·mixer_on_path − p2·bridge` (doc weights, in `ConfidenceWeights`), clamped [0,1], full `ConfidenceTerms` breakdown attached. `forward_trace(..., labels=LabelSet)` derives mixer/bridge sets from the pack, runs attribution, fills `TraceResult.vasp_candidates` + summary. Synthetic `fixtures/labels/aegis_demo_pack/` (DemoExchange VASP + DemoMixer). `ConfidenceTerms` relaxed to allow negative penalty weights (score = clamped weighted sum). `trace-fixture --labels/--no-labels`. 105 engine tests. |
| Frontend | Vite + React 18 + TS + Tailwind skeleton. Placeholder `App.tsx`. `eslint` (flat) + `tsc`/build + `vitest` configured. `/api` proxied to `:8000` in dev. |
| Containers | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (backend + frontend only). |
| Validation | `scripts/validate.sh` runs ruff/mypy/pytest + eslint/build/vitest. `pytest-timeout` (30s) so a stalled test fails loudly instead of hanging. |
| CI | `.github/workflows/ci.yml` — path-filtered backend/frontend jobs + `gitleaks` + `ci-ok` aggregation gate. |
| Docs | `docs/DATA_LICENSES.md` (stub), `docs/validation.md` (incl. branch-protection table + accepted deviation), `CLAUDE.md`, this file. |

## Not built yet (later phases — do not assume in code)

Live provider clients (TronGrid HTTP client is now Phase 4.5 in the vault plan;
no Ethereum — Phase 1D) · full wallet clustering (sweep-cluster construction —
only the `EndpointContext.cluster_addresses` hook exists; attribution's
via-cluster path is coded but unfed) · a real (non-synthetic) label pack · GNN
typology model (Phase 1E) · NLP complaint extraction (Phase 1F) · grounded LLM
report · **Phase 2 remainder**: rate limiting on trace-start + structured (JSON)
logging · Neo4j · WebSocket streaming · any real UI screen.

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
- 2026-09-04 — Phase 1C / **Gate M2**: `labels.py` (versioned checksum-verified
  packs; VASP vs sanctions kept distinct) + `attribution.py` (two-tier
  dataset-confirmed / heuristic / conflict / unknown, the transparent
  confidence formula with penalty terms). `forward_trace(labels=...)` runs it
  end to end; the demo pack yields "DemoExchange, dataset_confirmed, deposit
  THbK…, mixer penalty applied" with a mixer_like trail event. 105 engine
  tests. The evidence-first Tron trace → source-backed VASP path is complete.
- 2026-09-04 — Phase 2 started (PR #9): the trace HTTP API. `app/domain/`
  (`TraceService` + `InvestigationStore` interface + in-memory impl + wire
  schemas), `app/api/` (routes + `{error:{code,message,details}}` envelope),
  `app/engine_bridge.py`. `POST /api/v1/trace` → `GET /api/v1/trace/{id}` +
  `/graph`, on `BackgroundTasks`. `openapi.json` committed + CI-checked. 121
  tests.
- 2026-09-04 — Phase 2 persistence (PR #10): SQLAlchemy 2.0 + Alembic;
  `SqlInvestigationStore` behind the `InvestigationStore` interface (stores the
  full `Investigation` JSON + `result_hash`). `AEGIS_DATABASE_URL` (SQLite
  local / Postgres via Compose). `alembic check` in CI + `validate.sh`. Compose
  gains a `db` service; container entrypoint runs migrations. 125 tests.
- 2026-09-04 — Phase 2 auth (PR #11): JWT (PyJWT) + argon2. `app/security/` +
  `app/domain/accounts.py` (`AccountService`: authenticate / issue / rotating
  refresh) + `SqlAccountStore` (`users`, `refresh_tokens`, migration 0002).
  `/api/v1/auth/{login,refresh,me}`; trace routes now require a bearer token;
  `require_role`/`require_admin` ready for `/admin/*`. `scripts/create_user.py`.
  152 tests.
- 2026-09-04 — Phase 2 audit log (PR #12): hash-chained append-only `audit_log`
  (migration 0003). `AuditService.record/verify`; trace routes log
  start/complete/failed/read/read_graph with actor + `X-Request-ID`;
  `GET /api/v1/admin/audit` (admin) returns entries + a chain-verification pass;
  tamper-detection tests. 162 tests.
- 2026-09-04 — Phase 2 durable worker (PR #13): DB-backed job queue replaces
  `BackgroundTasks`. `claim_next` (lease + `FOR UPDATE SKIP LOCKED`), `TraceWorker`
  (`inline` thread or `python -m app.worker`), crash recovery via lease expiry,
  give-up after N attempts. Compose `worker` service. 170 tests.
- 2026-09-04 — Phase 2 case management (PR #14): `cases` + `complaints` tables
  (migration 0005), `CaseService` + `SqlCaseStore`, full CRUD under
  `/api/v1/cases`, trace↔case linkage (`POST /trace` 404s on unknown `case_id`),
  demo-only complaint text. Domain error base classes refactored. 183 tests.
- 2026-09-04 — Phase 2 report + notice (PR #15): `app/domain/reports.py` —
  `GET /api/v1/trace/{id}/report` (structured JSON: provenance, the confidence
  arithmetic, an s.63 certification block anchored on the result hash) and
  `POST /api/v1/trace/{id}/sahyog-notice` (preservation-request draft). 190
  tests. Next: rate limiting + structured logging (last Phase 2 PR).
