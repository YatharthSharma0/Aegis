"""Shared builders for engine records/results tests.

Everything is deterministic: fixed addresses, hashes, timestamps.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.engine.canonical import sha256_hex
from app.engine.records import (
    Asset,
    AssetKind,
    BlockRef,
    Chain,
    NormalizedTransaction,
    ProviderSnapshot,
    Transfer,
    TxStatus,
)

TS = datetime(2026, 8, 14, 19, 0, 0, tzinfo=UTC)
SEED = "TSeedAddr0000000000000000000000000000"
HOT = "THotWallet000000000000000000000000000"
TX = "0x" + "ab" * 32
USDT_TRC20 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


@pytest.fixture
def usdt() -> Asset:
    return Asset(
        chain=Chain.TRON,
        kind=AssetKind.TOKEN,
        symbol="USDT",
        decimals=6,
        contract=USDT_TRC20,
    )


@pytest.fixture
def tip_block() -> BlockRef:
    return BlockRef(
        chain=Chain.TRON, height=65_213_001, block_hash="0x" + "11" * 32, timestamp=TS
    )


@pytest.fixture
def snapshot(tip_block: BlockRef) -> ProviderSnapshot:
    return ProviderSnapshot(
        snapshot_id="snap-0001",
        provider="trongrid",
        chain=Chain.TRON,
        endpoint="/v1/accounts/{address}/transactions/trc20",
        request_params={"limit": "100", "contract_address": USDT_TRC20},
        captured_at=TS,
        tip_block=tip_block,
        response_checksum=sha256_hex(b"raw-response-bytes"),
        record_count=1,
    )


def make_transfer(
    usdt: Asset,
    *,
    value: str = "1499.500000",
    frm: str = SEED,
    to: str = HOT,
    snapshot_id: str = "snap-0001",
) -> Transfer:
    dec = Decimal(value)
    return Transfer(
        asset=usdt,
        from_address=frm,
        to_address=to,
        value=dec,
        value_raw=int(dec.scaleb(usdt.decimals)),
        tx_hash=TX,
        log_index=0,
        block_height=65_212_940,
        block_hash="0x" + "22" * 32,
        timestamp=TS,
        snapshot_id=snapshot_id,
    )


@pytest.fixture
def transfer(usdt: Asset) -> Transfer:
    return make_transfer(usdt)


@pytest.fixture
def normalized_tx(transfer: Transfer, tip_block: BlockRef) -> NormalizedTransaction:
    return NormalizedTransaction(
        chain=Chain.TRON,
        tx_hash=TX,
        status=TxStatus.SUCCESS,
        block=tip_block,
        from_address=SEED,
        to_address=USDT_TRC20,
        fee=Decimal("1.1"),
        transfers=(transfer,),
        snapshot_id="snap-0001",
    )
