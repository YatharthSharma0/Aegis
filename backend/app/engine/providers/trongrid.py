"""Live TronGrid adapter (execution-plan Phase 4.5).

A real ``ChainDataProvider`` against Tron mainnet via api.trongrid.io. Opt-in:
selected only when ``AEGIS_PROVIDER_MODE`` is ``live`` (or ``auto`` with a key
present) — the fixture stays the default everywhere else, including CI.

**The one real design decision this phase had to make** (see
``10-Execution-Plan/05a-Phase-4.5-Live-Provider-Integration.md``): TronGrid's
TRC-20 transfer-list endpoint returns a timestamp per transfer but no block
number or hash, while :class:`~app.engine.records.Transfer` requires both.
Resolution taken: enrich *every* transfer a page returns, not only the ones
that end up on the traced path — one extra call per unique transaction
(``wallet/gettransactioninfobyid``) and one per unique block
(``wallet/getblockbynum``, for the hash), both cached by id so a repeated or
overlapping fetch is free. This costs more calls on a cold cache than the
plan's "only the walked path" alternative, but requires zero changes to the
engine or to :class:`~app.engine.records.Transfer` — provenance is complete
for every transfer that reaches the walk, not just the subset that survives
pruning, which matches the project's "never a claim without evidence" rule
more directly.

Known limitation: :meth:`address_activity`'s ``transfer_count`` is not
populated (TronGrid's account endpoint doesn't expose one, and no engine
heuristic reads it today — see ``app/engine/walk.py``, only ``is_contract``
is consumed). ``first_seen``/``last_seen`` are best-effort from the account
endpoint's (inconsistently-spelled, across TronGrid API versions)
``create_time``/operation-time fields.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from app.engine.canonical import canonical_json, sha256_hex
from app.engine.errors import (
    ProviderRateLimitedError,
    ProviderResponseInvalidError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.engine.provider import DEFAULT_PAGE_SIZE, ActivityResult, BlockResult, TransferPage
from app.engine.providers.cache import ResponseCache
from app.engine.records import (
    Address,
    AddressActivity,
    Asset,
    BlockRef,
    Chain,
    NormalizedTransaction,
    ProviderSnapshot,
    Transfer,
    TxStatus,
)

logger = logging.getLogger("aegis.provider.trongrid")

BASE_URL = "https://api.trongrid.io"
PROVIDER_NAME = "trongrid"

_MAX_RETRIES = 4
_BACKOFF_BASE_S = 0.5
_BACKOFF_CAP_S = 8.0
_TIMEOUT_S = 10.0


class TronGridProvider:
    """A :class:`~app.engine.provider.ChainDataProvider` backed by live TronGrid."""

    name = PROVIDER_NAME
    chain = Chain.TRON

    def __init__(
        self,
        *,
        api_key: str,
        cache_dir: str | Path | None = None,
        base_url: str = BASE_URL,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("TronGridProvider requires a non-empty api_key")
        self._client = httpx.Client(
            base_url=base_url,
            # The key never appears in a log line, exception message, or
            # ProviderSnapshot — it only ever leaves this process as a header.
            headers={"TRON-PRO-API-KEY": api_key},
            timeout=_TIMEOUT_S,
            transport=transport,
        )
        self._cache = ResponseCache(cache_dir)
        self._sleep = sleep
        self._tx_info_cache: dict[str, dict[str, Any]] = {}
        self._block_hash_cache: dict[int, str] = {}

    def close(self) -> None:
        self._client.close()

    # -- ChainDataProvider ---------------------------------------------------

    def latest_block(self) -> BlockResult:
        body = self._call("wallet/getnowblock", {})
        header = body["block_header"]["raw_data"]
        block = BlockRef(
            chain=self.chain,
            height=header["number"],
            block_hash=body["blockID"],
            timestamp=_ms_to_dt(header["timestamp"]),
        )
        snapshot = self._snapshot(
            endpoint="wallet/getnowblock", params={}, raw=body, tip=block,
        )
        return BlockResult(block=block, snapshot=snapshot)

    def token_transfers(  # noqa: PLR0913 — mirrors the provider interface
        self,
        address: Address,
        *,
        asset: Asset,
        cursor: str | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        start_block: int | None = None,
        end_block: int | None = None,
    ) -> TransferPage:
        params: dict[str, Any] = {
            "contract_address": asset.contract,
            "limit": min(page_size, 200),
            "only_confirmed": "true",
        }
        if cursor:
            params["fingerprint"] = cursor
        if start_block is not None:
            params["min_block_timestamp"] = start_block
        if end_block is not None:
            params["max_block_timestamp"] = end_block

        body = self._call(f"v1/accounts/{address}/transactions/trc20", params)
        records: list[dict[str, Any]] = body.get("data", [])
        tip = self._current_tip()
        snapshot = self._snapshot(
            endpoint="v1/accounts/{address}/transactions/trc20",
            params={**params, "address": address},
            raw=body,
            tip=tip,
        )
        transactions = tuple(
            self._to_transaction(record, asset, snapshot.snapshot_id) for record in records
        )
        next_cursor = body.get("meta", {}).get("fingerprint") if records else None
        return TransferPage(transactions=transactions, snapshot=snapshot, next_cursor=next_cursor)

    def address_activity(self, address: Address) -> ActivityResult:
        body = self._call(f"v1/accounts/{address}", {})
        records = body.get("data", [])
        record = records[0] if records else {}
        create_time = record.get("create_time")
        # TronGrid's field name for last-activity time has varied across API
        # revisions; accept either rather than assume one.
        last_op = record.get("latest_operation_time") or record.get("latest_opration_time")
        activity = AddressActivity(
            chain=self.chain,
            address=address,
            is_contract=self._is_contract(address),
            first_seen=_ms_to_dt(create_time) if create_time else None,
            last_seen=_ms_to_dt(last_op) if last_op else None,
            # Not exposed by this endpoint; no current heuristic reads it
            # (see the module docstring) — left honestly at zero rather
            # than a fabricated estimate.
            transfer_count=0,
            snapshot_id=f"trongrid:activity:{address}",
        )
        snapshot = self._snapshot(
            endpoint="v1/accounts/{address}", params={"address": address}, raw=body,
            tip=self._current_tip(),
        )
        return ActivityResult(activity=activity, snapshot=snapshot)

    # -- transfer -> record enrichment ---------------------------------------

    def _to_transaction(
        self, record: dict[str, Any], asset: Asset, snapshot_id: str
    ) -> NormalizedTransaction:
        tx_hash = record["transaction_id"]
        tx_info = self._transaction_info(tx_hash)
        block_number = tx_info["blockNumber"]
        block_hash = self._block_hash(block_number)
        block = BlockRef(
            chain=self.chain,
            height=block_number,
            block_hash=block_hash,
            timestamp=_ms_to_dt(record["block_timestamp"]),
        )
        value_raw = int(record["value"])
        transfer = Transfer(
            asset=asset,
            from_address=record["from"],
            to_address=record["to"],
            value=Decimal(value_raw).scaleb(-asset.decimals),
            value_raw=value_raw,
            tx_hash=tx_hash,
            block_height=block_number,
            block_hash=block_hash,
            timestamp=block.timestamp,
            snapshot_id=snapshot_id,
        )
        return NormalizedTransaction(
            chain=self.chain,
            tx_hash=tx_hash,
            status=TxStatus.SUCCESS,
            block=block,
            from_address=record["from"],
            to_address=asset.contract,
            transfers=(transfer,),
            snapshot_id=snapshot_id,
        )

    def _transaction_info(self, tx_hash: str) -> dict[str, Any]:
        cached = self._tx_info_cache.get(tx_hash)
        if cached is not None:
            return cached
        body: dict[str, Any] = self._call("wallet/gettransactioninfobyid", {"value": tx_hash})
        if not body:
            raise ProviderResponseInvalidError(
                f"trongrid returned no transaction info for {tx_hash}"
            )
        self._tx_info_cache[tx_hash] = body
        return body

    def _block_hash(self, block_number: int) -> str:
        cached = self._block_hash_cache.get(block_number)
        if cached is not None:
            return cached
        body: dict[str, Any] = self._call("wallet/getblockbynum", {"num": block_number})
        block_id: str | None = body.get("blockID")
        if not block_id:
            raise ProviderResponseInvalidError(
                f"trongrid returned no blockID for block {block_number}"
            )
        self._block_hash_cache[block_number] = block_id
        return block_id

    def _is_contract(self, address: Address) -> bool:
        # wallet/* full-node RPCs default to hex addresses and reject a
        # base58 "T..." value with a parse error; `visible: true` tells
        # TronGrid to accept (and return) base58 instead — confirmed
        # against the real API, not assumed (a bare base58 value 400s).
        body = self._call("wallet/getcontract", {"value": address, "visible": True})
        return bool(body.get("bytecode"))

    def _current_tip(self) -> BlockRef:
        return self.latest_block().block

    # -- transport: cache -> retry -> HTTP -----------------------------------

    def _snapshot(
        self, *, endpoint: str, params: dict[str, Any], raw: Any, tip: BlockRef
    ) -> ProviderSnapshot:
        str_params = {k: str(v) for k, v in params.items() if v is not None}
        record_count = len(raw.get("data", [])) if isinstance(raw, dict) and "data" in raw else 1
        return ProviderSnapshot(
            snapshot_id=f"trongrid:{endpoint}:{sha256_hex(canonical_json(str_params))[:16]}",
            provider=self.name,
            chain=self.chain,
            endpoint=endpoint,
            request_params=str_params,
            captured_at=datetime.now(UTC),
            tip_block=tip,
            response_checksum=sha256_hex(canonical_json(raw)),
            record_count=record_count,
        )

    def _call(self, endpoint: str, params: dict[str, Any]) -> Any:
        cached = self._cache.get(self.name, endpoint, params)
        if cached is not None:
            return cached
        response = self._request_with_retry(endpoint, params)
        self._cache.put(self.name, endpoint, params, response)
        return response

    def _request_with_retry(self, endpoint: str, params: dict[str, Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            is_final = attempt == _MAX_RETRIES
            try:
                resp = self._send(endpoint, params)
            except httpx.TimeoutException as exc:
                if is_final:
                    raise ProviderTimeoutError(f"{endpoint} timed out") from exc
                last_error, retry_after = exc, None
            except httpx.TransportError as exc:
                if is_final:
                    raise ProviderUnavailableError(f"{endpoint} unreachable: {exc}") from exc
                last_error, retry_after = exc, None
            else:
                result = self._handle_response(resp, endpoint, is_final=is_final)
                if result is not None:
                    return result
                last_error, retry_after = None, _retryable_delay(resp)

            self._backoff(attempt, retry_after=retry_after)

        # Unreachable in practice (every branch above returns or raises on the
        # final attempt) — satisfies the type checker's control-flow analysis.
        raise ProviderUnavailableError(f"{endpoint} failed: {last_error}")

    def _send(self, endpoint: str, params: dict[str, Any]) -> httpx.Response:
        # TronGrid's full-node RPCs (wallet/*) are POST with a JSON body; the
        # v1 REST endpoints (v1/accounts/...) are GET with query params.
        if endpoint.startswith("wallet/"):
            return self._client.post(f"/{endpoint}", json=params)
        return self._client.get(f"/{endpoint}", params=params)

    @staticmethod
    def _handle_response(resp: httpx.Response, endpoint: str, *, is_final: bool) -> Any | None:
        """Return the parsed body, ``None`` to retry, or raise a terminal error."""
        if resp.status_code == httpx.codes.TOO_MANY_REQUESTS:
            if is_final:
                raise ProviderRateLimitedError(f"{endpoint} rate-limited by trongrid")
            return None
        if resp.status_code >= httpx.codes.INTERNAL_SERVER_ERROR:
            if is_final:
                raise ProviderUnavailableError(f"{endpoint} returned {resp.status_code}")
            return None
        if resp.status_code >= httpx.codes.BAD_REQUEST:
            raise ProviderResponseInvalidError(
                f"{endpoint} returned {resp.status_code}: {resp.text[:200]}"
            )
        try:
            body = resp.json()
        except ValueError as exc:
            raise ProviderResponseInvalidError(f"{endpoint} returned a non-JSON body") from exc
        # TronGrid's wallet/* full-node RPCs always answer 200, even on a bad
        # request — the failure is only visible as an {"Error": "..."} body.
        # Confirmed against the real API (a malformed value 200s with this
        # shape, not a 4xx) — not an assumption.
        if isinstance(body, dict) and "Error" in body:
            raise ProviderResponseInvalidError(f"{endpoint}: {body['Error']}")
        return body

    def _backoff(self, attempt: int, *, retry_after: float | None) -> None:
        delay = retry_after if retry_after is not None else min(
            _BACKOFF_BASE_S * (2**attempt), _BACKOFF_CAP_S
        )
        self._sleep(delay)


def _retryable_delay(response: httpx.Response) -> float | None:
    """The server-suggested retry delay, if any (only meaningful on a 429)."""
    if response.status_code != httpx.codes.TOO_MANY_REQUESTS:
        return None
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return float(header)
    except ValueError:
        return None


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)
