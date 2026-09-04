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

Every `/api/v1/trace*` route needs a bearer token. Create a user, log in, call:

```bash
uv run python scripts/create_user.py --email a@x.gov --name A --role officer --password 'password12345'

TOKEN=$(curl -s localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"a@x.gov","password":"password12345"}' | jq -r .access_token)

curl -sX POST localhost:8000/api/v1/trace -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"address":"TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"}'          # -> 202 {trace_id, ...}
curl -s localhost:8000/api/v1/trace/<trace_id>  -H "Authorization: Bearer $TOKEN"
curl -s localhost:8000/api/v1/trace/<trace_id>/graph -H "Authorization: Bearer $TOKEN"
```

`POST /auth/refresh` rotates the token pair. `POST /trace` only **queues** the
run; the durable worker executes it against the configured fixture
(`AEGIS_FIXTURE_ID`) + label packs (`AEGIS_LABEL_PACKS`). By default the worker
runs in-process (`AEGIS_TRACE_WORKER=inline`); Compose runs it as a separate
`worker` service (`external`). Every step is written to the hash-chained audit
log; `GET /api/v1/admin/audit` (admin role) returns the entries + a
chain-verification pass.

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
  api/             HTTP transport: routers (trace, auth), deps (+ current_user), error envelope
  domain/          TraceService, AccountService, store interfaces + in-memory + SQL impls
  security/        argon2 password hashing, JWT encode/decode
  db/              SQLAlchemy Base, ORM models, engine/session factory
  worker/          durable trace worker (claim + lease + retry); `python -m app.worker`
  engine_bridge.py the only place the backend calls app.engine
  engine/          Phase 1 blockchain analytics engine (pure library)
alembic/           migration environment + versions
openapi.json       committed schema; source of truth for frontend types
```

Keep configuration in `config.py` / `.env.example`; keep each layer boundary explicit.
