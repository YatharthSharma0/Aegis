"""Replay a recorded provider fixture. Deterministic, offline, no network.

A fixture directory holds ``manifest.json`` (id, chain, ``captured_at``,
``tip_block``, per-file sha256), ``transfers.json`` (TronGrid-shaped TRC-20
records) and ``activity.json`` (per-address footprint). On load the file
checksums are verified against the manifest — a mismatch raises
:class:`FixtureError`, so a corrupted or hand-edited fixture fails loudly.

Pagination is re-derived here (``offset:<n>`` cursors) rather than baked into the
files, so the same fixture exercises any ``page_size``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.engine.canonical import SCHEMA_VERSION, canonical_json, sha256_hex
from app.engine.errors import FixtureError, UnsupportedChainError
from app.engine.provider import DEFAULT_PAGE_SIZE, ActivityResult, BlockResult, TransferPage
from app.engine.records import (
    AddressActivity,
    Asset,
    BlockRef,
    Chain,
    NormalizedTransaction,
    ProviderSnapshot,
    Transfer,
    TxStatus,
)

DEFAULT_FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "fixtures"

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _ms_to_dt(ms: int) -> datetime:
    return _EPOCH + timedelta(milliseconds=ms)


def _parse_iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


class FixtureProvider:
    """A :class:`~app.engine.provider.ChainDataProvider` backed by recorded files."""

    def __init__(
        self, fixture_id: str, *, root: Path = DEFAULT_FIXTURE_ROOT
    ) -> None:
        self.fixture_id = fixture_id
        self._dir = root / fixture_id
        if not self._dir.is_dir():
            raise FixtureError(f"fixture directory not found: {self._dir}")

        manifest = self._load_json("manifest.json")
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise FixtureError(
                f"fixture {fixture_id} is schema {manifest.get('schema_version')!r}, "
                f"engine is {SCHEMA_VERSION!r}"
            )
        for name, meta in manifest["files"].items():
            actual = sha256_hex((self._dir / name).read_bytes())
            if actual != meta["sha256"]:
                raise FixtureError(
                    f"fixture {fixture_id}: {name} checksum mismatch "
                    f"(manifest {meta['sha256']}, file {actual})"
                )

        self.name: str = manifest["provider"]
        self.chain = Chain(manifest["chain"])
        self._captured_at = _parse_iso(manifest["captured_at"])
        tip = manifest["tip_block"]
        self._tip = BlockRef(
            chain=self.chain,
            height=tip["height"],
            block_hash=tip["block_hash"],
            timestamp=_parse_iso(tip["timestamp"]),
        )
        self._transfers: list[dict[str, Any]] = self._load_json("transfers.json")
        self._activity: dict[str, Any] = self._load_json("activity.json")

    # -- ChainDataProvider -------------------------------------------------

    def latest_block(self) -> BlockResult:
        snapshot = self._snapshot(
            endpoint="latest_block", params={}, raw=[self._tip.model_dump(mode="json")],
            suffix="tip",
        )
        return BlockResult(block=self._tip, snapshot=snapshot)

    def token_transfers(  # noqa: PLR0913 — mirrors the provider interface
        self,
        address: str,
        *,
        asset: Asset,
        cursor: str | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        start_block: int | None = None,
        end_block: int | None = None,
    ) -> TransferPage:
        if asset.chain is not self.chain:
            raise UnsupportedChainError(
                f"fixture serves {self.chain}, asset is {asset.chain}"
            )
        offset = _decode_cursor(cursor)
        matched = [
            record
            for record in self._transfers
            if record["token_info"]["address"] == asset.contract
            and address in (record["from"], record["to"])
            and (start_block is None or record["blockNumber"] >= start_block)
            and (end_block is None or record["blockNumber"] <= end_block)
        ]
        matched.sort(key=lambda r: (r["blockNumber"], r["block_timestamp"], r["transaction_id"]))
        window = matched[offset : offset + page_size]
        has_more = offset + page_size < len(matched)

        snapshot = self._snapshot(
            endpoint="/v1/accounts/{address}/transactions/trc20",
            params={
                "address": address,
                "contract_address": asset.contract or "",
                "limit": str(page_size),
                "offset": str(offset),
            },
            raw=window,
            suffix=f"trc20:{address}:{asset.contract}:{offset}",
        )
        transactions = _group_transactions(window, asset, self.chain, snapshot.snapshot_id)
        return TransferPage(
            transactions=transactions,
            snapshot=snapshot,
            next_cursor=f"offset:{offset + page_size}" if has_more else None,
        )

    def address_activity(self, address: str) -> ActivityResult:
        record = self._activity.get(address)
        if record is None:
            activity = AddressActivity(
                chain=self.chain, address=address, is_contract=False,
                transfer_count=0, snapshot_id=f"{self.fixture_id}:activity:{address}",
            )
            raw: list[dict[str, Any]] = []
        else:
            activity = AddressActivity(
                chain=self.chain,
                address=address,
                is_contract=bool(record["is_contract"]),
                first_seen=_ms_to_dt(record["first_seen_ms"]),
                last_seen=_ms_to_dt(record["last_seen_ms"]),
                transfer_count=int(record["transfer_count"]),
                snapshot_id=f"{self.fixture_id}:activity:{address}",
            )
            raw = [record]
        snapshot = self._snapshot(
            endpoint="/v1/accounts/{address}", params={"address": address},
            raw=raw, suffix=f"activity:{address}",
        )
        return ActivityResult(activity=activity, snapshot=snapshot)

    # -- internals -------------------------------------------------------

    def _load_json(self, name: str) -> Any:
        try:
            return json.loads((self._dir / name).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FixtureError(f"fixture {self.fixture_id}: missing {name}") from exc
        except json.JSONDecodeError as exc:
            raise FixtureError(f"fixture {self.fixture_id}: {name} is not valid JSON") from exc

    def _snapshot(
        self, *, endpoint: str, params: dict[str, str], raw: list[Any], suffix: str
    ) -> ProviderSnapshot:
        return ProviderSnapshot(
            snapshot_id=f"{self.fixture_id}:{suffix}",
            provider=self.name,
            chain=self.chain,
            endpoint=endpoint,
            request_params=params,
            captured_at=self._captured_at,
            tip_block=self._tip,
            response_checksum=sha256_hex(canonical_json(raw)),
            record_count=len(raw),
            notes="synthetic fixture replay",
        )


def _decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    prefix, _, value = cursor.partition(":")
    if prefix != "offset" or not value.isdigit():
        raise FixtureError(f"unrecognised cursor: {cursor!r}")
    return int(value)


def _group_transactions(
    records: list[dict[str, Any]], asset: Asset, chain: Chain, snapshot_id: str
) -> tuple[NormalizedTransaction, ...]:
    by_tx: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for record in records:
        tx_id = record["transaction_id"]
        if tx_id not in by_tx:
            by_tx[tx_id] = []
            order.append(tx_id)
        by_tx[tx_id].append(record)

    out: list[NormalizedTransaction] = []
    for tx_id in order:
        group = by_tx[tx_id]
        transfers = tuple(
            _to_transfer(record, asset, snapshot_id, log_index)
            for log_index, record in enumerate(group)
        )
        head = group[0]
        out.append(
            NormalizedTransaction(
                chain=chain,
                tx_hash=tx_id,
                status=TxStatus.SUCCESS,
                block=BlockRef(
                    chain=chain,
                    height=head["blockNumber"],
                    block_hash=head["blockHash"],
                    timestamp=_ms_to_dt(head["block_timestamp"]),
                ),
                from_address=head["from"],
                to_address=asset.contract,
                transfers=transfers,
                snapshot_id=snapshot_id,
            )
        )
    return tuple(out)


def _to_transfer(
    record: dict[str, Any], asset: Asset, snapshot_id: str, log_index: int
) -> Transfer:
    value_raw = int(record["value"])
    return Transfer(
        asset=asset,
        from_address=record["from"],
        to_address=record["to"],
        value=Decimal(value_raw).scaleb(-asset.decimals),
        value_raw=value_raw,
        tx_hash=record["transaction_id"],
        log_index=log_index,
        block_height=record["blockNumber"],
        block_hash=record["blockHash"],
        timestamp=_ms_to_dt(record["block_timestamp"]),
        snapshot_id=snapshot_id,
    )
