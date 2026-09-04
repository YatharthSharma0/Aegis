# Deployment (Phase 6 — staging)

A public staging deployment for demos and hackathon judging — not a
hardened commercial deployment. This system reads public chain data and
never custodies assets; "production" here means a stable public URL, not
a production-for-real-funds environment. State this explicitly to judges.

## Topology

| Component | Platform | Notes |
|---|---|---|
| Frontend (`frontend/`) | Vercel | Static Vite build, `vercel --prod` from `frontend/`. No GitHub integration configured yet (see "Known gaps" below) — deploys are CLI-triggered, not automatic on push. |
| Backend API (`backend/`) | Railway, service `aegis-backend` | Deployed from `backend/` via `railway up backend --path-as-root --service aegis-backend`. Runs migrations on boot (`docker-entrypoint.sh`). Public domain via `railway domain`. |
| Worker (`backend/`) | Railway, service `aegis-worker` | Same source/build as the backend. **Known gap:** intended to run only `python -m app.worker` (`AEGIS_TRACE_WORKER=external` on the API), but Railway's CLI has no way to set a per-service custom start command — only the dashboard does (Service → Settings → Deploy → Custom Start Command), and it did not visibly take effect after being set once. Currently runs the full API image with its own **inline** worker thread (`AEGIS_TRACE_WORKER` left at its `inline` default on this service only) — functionally processes the trace queue correctly (verified), just runs a redundant full API process to do it. Revisit via the dashboard when there's time to confirm the start command sticks after a rebuild. |
| Database | Railway Postgres plugin | Managed, same project. `AEGIS_DATABASE_URL` on both `aegis-backend`/`aegis-worker` is a Railway variable reference built from the plugin's `PGUSER`/`PGPASSWORD`/`PGHOST`/`PGPORT`/`PGDATABASE` vars — **not** the plugin's own `DATABASE_URL`, which defaults to a bare `postgresql://` scheme (psycopg2 driver); this repo only has `psycopg` (v3) installed, so that URL 500s on connect. Always rebuild it with the `postgresql+psycopg://` scheme. |

No Neo4j / graph database — this repo never adopted one (Postgres/SQLite only; Cytoscape.js renders the graph client-side). The original vault plan's Neo4j Aura row doesn't apply here.

## Environment variables (names only — values live in each platform's dashboard, never here)

**`aegis-backend`** — every key in `backend/.env.example`, plus:
- `AEGIS_ENVIRONMENT=staging`
- `AEGIS_TRACE_WORKER=external` (the separate worker service drains the queue)
- `AEGIS_PROVIDER_MODE=fixture` (deliberate — see "Why fixture mode" below)
- `AEGIS_CORS_ORIGINS` set to the exact deployed Vercel origin (JSON array, one entry — never `*`)
- `AEGIS_JWT_SECRET` a real generated value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) — never the repo's dev default

**`aegis-worker`** — `AEGIS_DATABASE_URL` (same as above), `AEGIS_SKIP_MIGRATIONS=1` (the API service already runs them), `AEGIS_ENVIRONMENT=staging`, `AEGIS_LOG_JSON=true`, `AEGIS_PROVIDER_MODE=fixture`.

**Vercel (`aegis-frontend`)** — `VITE_API_BASE_URL` set to the deployed backend's origin (no trailing slash; `frontend/.env.example` documents this is empty/relative in local dev, where Vite proxies `/api`).

## Why fixture mode on staging

`AEGIS_PROVIDER_MODE=fixture` is deliberate, not a placeholder. Live mode
(`docs/PROVIDERS.md`, Phase 4.5) has a real API key working locally, but
staging traffic (judges clicking around, repeated demo runs) should never
depend on TronGrid's uptime or a shared rate budget. The fixture is
deterministic and offline — every demo run produces the same, already-
verified result.

## Demo data

Five realistic cases (fictional, `is_demo=true` complaints — real complaint
text is refused server-side regardless, see `docs/SECURITY.md`'s DPDP row)
were seeded directly via the deployed API for judging/demo purposes:
different ref numbers, titles, complaint narratives, and case statuses
(open/in_progress/closed) for a populated-looking dashboard. Every case's
underlying trace runs against the same `growjoy_tron_trc20` fixture seed
address — fixture mode has only one recorded dataset, so trace *content*
is identical across cases even though the case narratives differ. No seed
script was added to the repo for this (one-off, run via a throwaway local
script against the live API) — worth promoting to a committed
`backend/scripts/seed_demo_cases.py` if repeat demo-data seeding becomes a
regular need.

## Known gaps

- **No CI staging deploy job.** All deploys so far are manual CLI
  invocations (`railway up`, `vercel --prod`), not gated on `main` passing
  CI. The vault's Phase 6 task list calls for a `deploy` CI job — not
  built yet.
- **No GitHub integration on either platform** — Vercel's repo link failed
  (`Login Connection` to GitHub not configured on this Vercel account) and
  Railway was never connected to the repo either. Every redeploy today was
  a manual `railway up` / `vercel --prod` from a local checkout. Fine for
  a hackathon demo; revisit before relying on this for anything longer-
  lived — auto-deploy-on-push and preview deployments are exactly what
  Vercel/Railway are good at and neither is wired up yet.
- **Worker start command** — see the topology table above.
- **No rollback rehearsal.** The vault's rollback strategy (Vercel's
  instant prior-deployment rollback, Railway redeploy-previous-image,
  never assume free-tier Postgres has PITR) is documented there but
  untested against this actual deployment.

## Redeploying

```bash
# Backend (from repo root)
railway up backend --path-as-root --service aegis-backend

# Worker (same source, different service)
railway up backend --path-as-root --service aegis-worker

# Frontend
cd frontend && vercel --prod
```

Requires `railway login` / `vercel login` (browser-based) once per machine
— see `~/.railway/bin` on PATH if the curl installer was used instead of
an npm global install.
