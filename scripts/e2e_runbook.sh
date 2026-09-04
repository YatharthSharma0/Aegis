#!/usr/bin/env bash
# Phase 4 end-to-end runbook: address in -> traced flow -> attributed VASP ->
# evidence-grade report out, against a real Docker Compose stack. This is the
# committed, repeatable version of the demo path previously only run ad hoc
# via curl (see repo MEMORY.md, "Phase 4" entries).
#
# Usage:
#   ./scripts/e2e_runbook.sh            # bring the stack up, run the flow, leave it running
#   ./scripts/e2e_runbook.sh --down     # also tear the stack down on exit (success or failure)
#
# What it proves: POST /trace (backend, enqueue-only) -> a separate `worker`
# container claims the row over real Postgres -> GET /trace/{id} polling
# reaches `done` -> the report reflects the same result hash. Requires the
# `docker`, `curl`, `jq`, and `python3` CLIs.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TEAR_DOWN=0
if [[ "${1:-}" == "--down" ]]; then
  TEAR_DOWN=1
fi

BASE_URL="http://localhost:8000"
EMAIL="e2e-runbook@aegis.local"
PASSWORD="e2e-runbook-password-not-for-prod"
SEED_ADDRESS="TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"   # growjoy_tron_trc20 fixture seed
POLL_TIMEOUT_S=30

step() { echo; echo "==> $*"; }

cleanup() {
  if [[ "$TEAR_DOWN" == 1 ]]; then
    step "tearing down the stack (--down)"
    docker compose down
  fi
}
trap cleanup EXIT

step "docker compose up -d --wait"
docker compose up -d --wait

step "provisioning the runbook test user (idempotent)"
docker compose exec -T backend uv run python scripts/create_user.py \
  --email "$EMAIL" --name "E2E Runbook" --role officer --password "$PASSWORD" \
  || echo "  (already exists — continuing)"

step "logging in"
LOGIN_JSON="$(curl -sf -X POST "$BASE_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")"
ACCESS_TOKEN="$(echo "$LOGIN_JSON" | jq -r .access_token)"
if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  echo "login failed: $LOGIN_JSON" >&2
  exit 1
fi
AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"

step "starting a trace on $SEED_ADDRESS"
TRACE_JSON="$(curl -sf -X POST "$BASE_URL/api/v1/trace" \
  -H "$AUTH_HEADER" -H 'Content-Type: application/json' \
  -d "{\"address\":\"$SEED_ADDRESS\"}")"
TRACE_ID="$(echo "$TRACE_JSON" | jq -r .trace_id)"
echo "  trace_id=$TRACE_ID"

step "polling until terminal (timeout ${POLL_TIMEOUT_S}s)"
deadline=$((SECONDS + POLL_TIMEOUT_S))
STATUS="queued"
while [[ "$STATUS" != "done" && "$STATUS" != "partial" && "$STATUS" != "failed" ]]; do
  if (( SECONDS > deadline )); then
    echo "trace did not finish within ${POLL_TIMEOUT_S}s (last status: $STATUS)" >&2
    exit 1
  fi
  sleep 1
  STATUS_JSON="$(curl -sf "$BASE_URL/api/v1/trace/$TRACE_ID" -H "$AUTH_HEADER")"
  STATUS="$(echo "$STATUS_JSON" | jq -r .status)"
  echo "  status=$STATUS"
done

if [[ "$STATUS" != "done" ]]; then
  echo "trace ended in status '$STATUS', not 'done': $STATUS_JSON" >&2
  exit 1
fi
RESULT_HASH="$(echo "$STATUS_JSON" | jq -r .result_hash)"
echo "  result_hash=$RESULT_HASH"

step "fetching the evidence-grade report"
REPORT_JSON="$(curl -sf "$BASE_URL/api/v1/trace/$TRACE_ID/report" -H "$AUTH_HEADER")"
REPORT_HASH="$(echo "$REPORT_JSON" | jq -r .header.result_hash)"
if [[ "$REPORT_HASH" != "$RESULT_HASH" ]]; then
  echo "report result_hash ($REPORT_HASH) doesn't match the trace's ($RESULT_HASH)" >&2
  exit 1
fi

echo
echo "PASS — trace $TRACE_ID completed end to end (result_hash=$RESULT_HASH)"
