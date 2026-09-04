#!/bin/sh
# Run migrations, then hand off to the container command (uvicorn).
set -e
echo "==> alembic upgrade head"
uv run --no-dev alembic upgrade head
exec "$@"
