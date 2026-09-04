#!/bin/sh
# Run migrations (unless told to skip — e.g. the worker, since the API already
# ran them), then hand off to the container command.
set -e
if [ "${AEGIS_SKIP_MIGRATIONS:-0}" != "1" ]; then
  echo "==> alembic upgrade head"
  uv run --no-dev alembic upgrade head
fi
exec "$@"
