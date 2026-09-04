# Security checklist (Phase 5)

Evidence-based status of the security checklist in the design vault's
`10-Execution-Plan/06-Phase-5-Testing-Security.md`. Each item links to the
test, CI job, or code that proves it — not asserted from memory. Updated
whenever an item's status changes.

**Explicit scope limit:** this is engineering-level verification (automated
scanning + tests), not a professional third-party security audit. That is
out of scope and unnecessary for a hackathon prototype holding no real
funds and no real victim data — say so plainly wherever this posture is
described (pitch, README, judge Q&A), per the vault's own framing.

## Checklist

| Item | Status | Evidence |
|---|---|---|
| Secrets never reach Git | ✅ | `.gitignore` (`.env`, `.env.*`, `*.pem`, `*.key`); `gitleaks` job (`.github/workflows/ci.yml` `secret-scan`) on every push/PR, extended by `.gitleaks.toml` for the TronGrid key shape (Phase 4.5) |
| Input validation matches documented limits | ✅ | Every request body is a `pydantic` model with `extra="forbid"` (`app/domain/schemas.py`) — an unknown field is a 422, not silently ignored; field-level constraints (`min_length`, `ge`/`le`) match `04-Constraints-and-Assumptions.md` |
| AuthN: invalid/expired/malformed tokens rejected | ✅ | `backend/tests/security/test_tokens.py` (expired, tampered, wrong-secret, access-used-as-refresh); `backend/tests/api/test_auth_routes.py::test_malformed_bearer_is_401`, `test_me_without_a_token_is_401` |
| AuthZ: admin-only routes actually gated | ✅ | `backend/tests/api/test_admin_routes.py::test_audit_requires_admin` — the only role boundary in the product (officer/analyst/admin are otherwise undifferentiated by design; there is no broader RBAC surface to test) |
| Rate limiting actually throttles | ✅ | `backend/tests/api/test_ratelimit_and_logging.py` — unit tests on the limiter itself (window rollover, limit=0 disables) *and* HTTP-level tests that the 4th request in a window gets a real 429 with `Retry-After` on both `/trace` and `/auth/login` |
| CORS origin is explicit, never `*` | ✅ | `app/config.py` `cors_origins` defaults to `["http://localhost:5173"]`; `backend/.env.example` documents it as a JSON array to set explicitly per environment; nothing in the codebase sets or suggests `"*"` |
| XSS: no unsanitized HTML injection | ✅ | `grep -r dangerouslySetInnerHTML frontend/src` — zero matches. Report and SAHYOG-notice content render as plain React text nodes |
| Dependency scanning in CI | ✅ | `uv run pip-audit` (backend) and `npm audit --omit=dev` (frontend), both in `scripts/validate.sh` and `.github/workflows/ci.yml` as of Phase 5. Zero known vulnerabilities as of 2026-09-05 |
| DPDP: no real victim complaint text stored | ✅ | `CaseService.attach_complaint` (`app/domain/cases.py`) hard-refuses any complaint where `is_demo` is not `true` — `InvalidRequestError("real complaint text cannot be stored yet — encryption + retention policy pending")`. This is enforced server-side, not merely documented; see `backend/tests/domain/test_cases.py::test_real_complaint_is_refused`. Encryption-at-rest and a retention policy remain **not built** — real complaint ingestion stays fully gated until they are, so there is nothing sensitive at rest to encrypt yet |
| No unauthenticated admin API | ✅ | Every route on `routes_admin.py` sits behind `Depends(require_admin)`; `test_audit_requires_admin` covers the negative case (officer token → 403) |
| Migration reversibility (up/down) | ✅ | Phase 5: `scripts/validate.sh` and CI now run `alembic upgrade head` → `alembic check` → `alembic downgrade base` → `alembic upgrade head` on a scratch SQLite DB, proving every migration has a working `downgrade()`, not just `upgrade()` |
| Taint-walk invariants | ✅ | Already covered pre-Phase-5: `backend/tests/engine/test_walk.py::test_taint_is_conserved_along_every_path`, `test_clean_fan_in_dilutes_but_tainted_fan_in_accumulates` |
| Clustering/typology-heuristic defeat cases | ✅ | Already covered pre-Phase-5: `backend/tests/engine/test_signals.py` (rotation, peel chain, fan-in/fan-out, seed-never-flagged, partial-forward-doesn't-look-like-rotation) |
| Full-stack E2E flow | ✅ | Already covered pre-Phase-5 (Phase 4): `backend/tests/integration/` (12 tests against a live Docker Compose stack) + `scripts/e2e_runbook.sh` for a scripted manual demo run. Chosen over browser automation (Playwright) because no browser-automation tooling was available in this environment — documented as a deliberate substitution, not a silent gap |
| GNN eval reproducibility | N/A — `not_scored` | Phase 1E (GNN typology model) was never built (deferred, see repo `MEMORY.md` "Deferred"). No `EVAL.md` exists; none should — creating one now would imply a metric that doesn't exist. State `not_scored` / "not built" explicitly in the pitch and judge Q&A, never omit or imply otherwise |
| Professional third-party audit | Explicitly out of scope | Stated here and in the pitch — a prototype holding no real funds/victim data doesn't warrant one; automated scanning above is not presented as equivalent |

## What Phase 5 actually added

Everything above marked with a pre-existing test was already covered by
Phases 0–4.5's own test discipline — Phase 5's job was to *audit and
evidence* that, not originate it from scratch, per the vault's own framing
("this is not the first point at which security or tests are added"). The
concrete gaps Phase 5 found and closed:

1. **No dependency scanning in CI.** Added `pip-audit` (backend) and `npm
   audit --omit=dev` (frontend) to both `scripts/validate.sh` and CI.
2. **Migrations were only ever tested upgrading.** Added a downgrade-to-base
   round trip so a broken `downgrade()` fails CI, not just a broken
   `upgrade()`.

## Known gaps, honestly stated

- **Encryption-at-rest for complaint text** is not built. Real (non-demo)
  complaint text is refused at the API boundary instead — a stronger
  guarantee for a prototype (nothing sensitive can land in the database at
  all) but not the same thing as the vault's original "encrypt it" plan.
  Revisit if/when real complaint ingestion is scoped in.
- **Phase 4.5's live-provider gaps** (no live-recorded regression fixture,
  no real end-to-end live smoke test, unverified TronGrid field-name
  assumptions) are tracked in `docs/PROVIDERS.md` and `MEMORY.md`, not
  repeated here — they're a live-data-correctness gap, not a security one.
- **E2E automation is Docker-Compose-based `pytest`, not a browser tool**
  (Playwright etc.) — a deliberate substitution given this environment's
  tooling, not a silent scope cut. See the table row above.
