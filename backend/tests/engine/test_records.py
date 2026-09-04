"""Internal normalized records: validation and provenance rules."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine.canonical import canonical_hash
from app.engine.records import (
    AddressActivity,
    Asset,
    AssetKind,
    Chain,
    NormalizedTransaction,
    Transfer,
    TxStatus,
)
from tests.engine.conftest import SEED, TS, TX, USDT_TRC20, make_transfer


def test_native_asset_must_not_have_contract():
    with pytest.raises(ValidationError):
        Asset(chain=Chain.TRON, kind=AssetKind.NATIVE, symbol="TRX", decimals=6,
              contract=USDT_TRC20)


def test_token_asset_must_have_contract():
    with pytest.raises(ValidationError):
        Asset(chain=Chain.TRON, kind=AssetKind.TOKEN, symbol="USDT", decimals=6)


def test_records_are_frozen_and_reject_unknown_fields(usdt: Asset):
    with pytest.raises(ValidationError):
        Asset(chain=Chain.TRON, kind=AssetKind.NATIVE, symbol="TRX", decimals=6,
              surprise=1)
    with pytest.raises(ValidationError):
        usdt.symbol = "ETH"  # type: ignore[misc]


def test_transfer_value_and_value_raw_must_agree(usdt: Asset):
    with pytest.raises(ValidationError):
        Transfer(
            asset=usdt, from_address=SEED, to_address=SEED,
            value=Decimal("1.000000"), value_raw=999_999,  # should be 1_000_000
            tx_hash=TX, block_height=1, block_hash=TX, timestamp=TS,
            snapshot_id="s",
        )


def test_transfer_value_must_be_quantized_to_asset_decimals(usdt: Asset):
    with pytest.raises(ValidationError):
        Transfer(
            asset=usdt, from_address=SEED, to_address=SEED,
            value=Decimal("1.1234567"), value_raw=1_123_456,
            tx_hash=TX, block_height=1, block_hash=TX, timestamp=TS, snapshot_id="s",
        )


def test_transfer_roundtrips_when_consistent(transfer: Transfer):
    assert transfer.value == Decimal("1499.500000")
    assert transfer.value_raw == 1_499_500_000


def test_normalized_tx_rejects_transfer_from_a_different_tx(usdt: Asset, tip_block):
    alien = make_transfer(usdt)
    alien = alien.model_copy(update={"tx_hash": "0x" + "cd" * 32})
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            chain=Chain.TRON, tx_hash=TX, status=TxStatus.SUCCESS, block=tip_block,
            from_address=SEED, transfers=(alien,), snapshot_id="snap-0001",
        )


def test_normalized_tx_rejects_transfer_from_a_different_snapshot(usdt: Asset, tip_block):
    other = make_transfer(usdt, snapshot_id="snap-9999")
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            chain=Chain.TRON, tx_hash=TX, status=TxStatus.SUCCESS, block=tip_block,
            from_address=SEED, transfers=(other,), snapshot_id="snap-0001",
        )


def test_address_activity_seen_order_is_validated():
    later = TS
    earlier = TS - timedelta(days=1)
    with pytest.raises(ValidationError):
        AddressActivity(
            chain=Chain.TRON, address=SEED, is_contract=False,
            first_seen=later, last_seen=earlier, transfer_count=3, snapshot_id="s",
        )


def test_snapshot_canonical_hash_is_stable(snapshot):
    assert canonical_hash(snapshot) == canonical_hash(snapshot.model_copy(deep=True))


def test_snapshot_canonical_hash_ignores_naive_now(snapshot):
    # captured_at is provenance and *is* part of the hash; changing it changes it.
    moved = snapshot.model_copy(
        update={"captured_at": datetime(2027, 1, 1, tzinfo=UTC)}
    )
    assert canonical_hash(moved) != canonical_hash(snapshot)
