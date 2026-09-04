#!/usr/bin/env bash
# The single local check gate. Runs everything CI runs.
# Usage: ./scripts/validate.sh [backend|frontend]   (default: both)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-both}"

run_backend() {
  echo "==> backend: ruff / mypy / pytest / openapi / migrations"
  cd "$ROOT/backend"
  uv run ruff check .
  uv run mypy app
  uv run pytest
  uv run python scripts/export_openapi.py >/dev/null
  git -C "$ROOT" diff --exit-code backend/openapi.json
  local drift_db
  drift_db="$(mktemp -u).db"
  AEGIS_DATABASE_URL="sqlite:///$drift_db" uv run alembic upgrade head >/dev/null
  AEGIS_DATABASE_URL="sqlite:///$drift_db" uv run alembic check >/dev/null
  rm -f "$drift_db"
}

run_frontend() {
  echo "==> frontend: eslint / tsc + build / vitest"
  cd "$ROOT/frontend"
  npm run lint
  npm run build
  npm run test
}

case "$TARGET" in
  backend) run_backend ;;
  frontend) run_frontend ;;
  both) run_backend; run_frontend ;;
  *) echo "unknown target: $TARGET (expected backend|frontend|both)" >&2; exit 2 ;;
esac

echo "==> all checks passed"
