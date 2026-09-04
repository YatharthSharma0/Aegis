# Aegis backend

Python 3.12 · FastAPI. Managed with [`uv`](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync --extra dev        # create .venv (Python 3.12) with runtime + dev deps
cp .env.example .env       # optional; defaults work for local dev
```

## Run

```bash
uv run uvicorn app.main:app --reload
# http://localhost:8000/health   http://localhost:8000/docs
```

## Trace API (Phase 2)

```bash
curl -sX POST localhost:8000/api/v1/trace \
  -H 'content-type: application/json' \
  -d '{"address":"TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"}'          # -> 202 {trace_id, ...}
curl -s localhost:8000/api/v1/trace/<trace_id>                   # status + result
curl -s localhost:8000/api/v1/trace/<trace_id>/graph             # nodes + edges
```

Runs the Phase 1 engine on a `BackgroundTask` against the configured fixture
(`AEGIS_FIXTURE_ID`) + label packs (`AEGIS_LABEL_PACKS`). Persistence, auth, a
durable worker, and the audit log land in later Phase 2 PRs.

## Database

SQLAlchemy 2.0 + Alembic. Local dev defaults to a file SQLite DB
(`AEGIS_DATABASE_URL`); Compose runs Postgres and the container entrypoint
applies migrations on boot. Non-production processes also create tables on
startup, so `uvicorn app.main:app` just works.

```bash
uv run alembic upgrade head          # apply migrations
uv run alembic revision --autogenerate -m "add X"   # after changing app/db/models.py
uv run alembic check                 # fail if models and migrations disagree
```

## Checks

```bash
uv run ruff check .
uv run mypy app
uv run pytest
uv run python scripts/export_openapi.py   # regenerate openapi.json (CI checks it)
uv run alembic upgrade head && uv run alembic check   # migration drift (CI checks it)
```

## Layout

```
app/
  main.py          FastAPI app + health + lifespan (create_all in non-prod)
  config.py        environment-driven settings (the only place env vars are read)
  api/             HTTP transport: routers, deps, error envelope
  domain/          TraceService, InvestigationStore + in-memory + SQL impls, wire schemas
  db/              SQLAlchemy Base, ORM models, engine/session factory
  engine_bridge.py the only place the backend calls app.engine
  engine/          Phase 1 blockchain analytics engine (pure library)
alembic/           migration environment + versions
openapi.json       committed schema; source of truth for frontend types
```

Keep configuration in `config.py` / `.env.example`; keep each layer boundary explicit.
