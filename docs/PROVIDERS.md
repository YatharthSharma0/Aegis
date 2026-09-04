# Chain data providers

The engine reads chain data through the `ChainDataProvider` interface
(`backend/app/engine/provider.py`, frozen since Phase 1A) — a trace never
knows or cares which implementation it got.

## Modes (`AEGIS_PROVIDER_MODE`)

| Mode | Behaviour |
|---|---|
| `fixture` (default) | Always the recorded synthetic fixture (`AEGIS_FIXTURE_ID`, default `growjoy_tron_trc20`). Offline, deterministic, zero network calls. This is the CI and offline-demo path — it never changes based on whether a key is configured. |
| `live` | Always `TronGridProvider` against real Tron mainnet. Requires `AEGIS_TRONGRID_API_KEY`; raises a configuration error at provider-construction time if it's missing, or if a non-Tron chain is requested (no live adapter exists yet — see Phase 1D). |
| `auto` | `live` if `AEGIS_TRONGRID_API_KEY` is set and the chain is Tron, else `fixture`. Lets a deployment silently fall back to the fixture rather than failing if the key was never configured. |

Selection happens in one place: `app.engine.providers.get_provider(chain, mode, ...)`.
The backend (`app/engine_bridge.py`) and the CLI (`python -m app.engine
trace-fixture --live`) both call it — nothing downstream branches on mode.

## Getting a TronGrid key

1. Sign up at [trongrid.io](https://www.trongrid.io/) (free tier is enough for
   development and rehearsal).
2. Copy the key into `backend/.env`:
   ```
   AEGIS_TRONGRID_API_KEY=<your key>
   AEGIS_PROVIDER_MODE=auto   # or live
   ```
3. **Never** commit a real key. `backend/.env` is git-ignored;
   `backend/.env.example` only ever holds an empty placeholder. `gitleaks`
   runs on every CI push and PR and will fail the build on a committed
   secret-shaped string (see `.gitleaks.toml`).

The key is only ever read from the environment (`app/config.py`), only ever
sent as the `TRON-PRO-API-KEY` request header, and is never written into a
`ProviderSnapshot`, a log line, or an exception message — verified by
`backend/tests/engine/providers/test_trongrid.py`
(`test_api_key_never_appears_in_a_raised_error_message` and the request-params
assertion in `test_latest_block_parses_tip_from_getnowblock`).

## The provenance gap TronGrid has, and how it's resolved

TronGrid's TRC-20 transfer-list endpoint
(`/v1/accounts/{address}/transactions/trc20`) returns a transaction id and a
timestamp per transfer, but no block number or hash — and
`app.engine.records.Transfer` requires both (every claim in an evidence-grade
report must trace back to a specific block).

**Resolution:** `TronGridProvider` enriches *every* transfer a page returns,
not only the ones that end up on the walked path:
- `wallet/gettransactioninfobyid` (once per unique `tx_hash`, cached) for the
  block number,
- `wallet/getblockbynum` (once per unique block number, cached) for the block
  hash.

This is a deliberate deviation from the execution plan's "enrich only
walked-path transfers" suggestion — that would need the engine to call back
into the provider *after* the walk decides what survived pruning, which
doesn't exist today and would touch `app/engine/walk.py`. Enriching eagerly
costs more calls on a cold cache (bounded by the number of *unique*
transactions and blocks a page touches, not the number of transfers — a
single Tron block holds many transactions) but requires zero engine changes
and guarantees full provenance for every transfer the walk ever sees, not
just the subset that made it into the final result.

## Retry, rate limits, and failure

Every TronGrid call retries with exponential backoff (capped) on a timeout,
a transport error, a 5xx, or a 429 — honoring the 429's `Retry-After` header
when present. After the retry budget is exhausted:

| Failure | Raised |
|---|---|
| Timeout | `ProviderTimeoutError` |
| Transport error (DNS, connection refused, …) | `ProviderUnavailableError` |
| 5xx | `ProviderUnavailableError` |
| 429 | `ProviderRateLimitedError` |
| 4xx (other) | `ProviderResponseInvalidError` — not retried, it won't succeed on repeat |
| Non-JSON / unparseable body | `ProviderResponseInvalidError` |

A `ProviderRateLimitedError` or `ProviderUnavailableError` surfacing out of
a trace run becomes a `status: partial` result with reason
`provider_rate_limited` / `provider_unavailable` (see
`app.engine.errors.PartialReason`) — never a fabricated or silently-truncated
result.

## Response cache (`AEGIS_PROVIDER_CACHE_DIR`)

Every live call is cached on disk, keyed by `(provider, endpoint, params)` —
the exact request shape. A repeated trace against the same addresses makes
zero live calls once the cache is warm (the Phase 4.5 mitigation for a
rehearsed demo not depending on TronGrid's uptime or your remaining rate
budget on stage). The cache never expires or invalidates on its own — delete
the directory (default `backend/.provider-cache/`, git-ignored) to force
fresh calls. Leave `AEGIS_PROVIDER_CACHE_DIR` empty to disable caching
entirely.

## What's not built yet

- **No recorded live regression fixture yet.** The plan calls for committing
  one real trace (public address, documented provenance) recorded from live
  TronGrid, alongside the synthetic `growjoy_tron_trc20` fixture. Deferred
  until a TronGrid key is available in this environment to record it.
- **`address_activity`'s `transfer_count` is always `0`.** TronGrid's account
  endpoint doesn't expose a transfer count, and no current engine heuristic
  reads it (`app/engine/walk.py` only consumes `is_contract`) — left honestly
  unpopulated rather than estimated.
- Ethereum and every other non-Tron chain: no live adapter (Phase 1D).
