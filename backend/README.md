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

## Checks

```bash
uv run ruff check .
uv run mypy app
uv run pytest
```

## Layout

```
app/
  main.py      FastAPI app + routes
  config.py    environment-driven settings (the only place env vars are read)
tests/
  test_health.py
```

Later phases add the blockchain analytics engine, persistence (PostgreSQL, Neo4j),
Celery workers, and the AI components. Keep configuration in `config.py` /
`.env.example`; keep each layer boundary explicit.
