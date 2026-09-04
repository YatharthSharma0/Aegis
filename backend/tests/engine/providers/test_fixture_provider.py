"""FixtureProvider: deterministic replay, pagination, checksum integrity."""

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine.canonical import canonical_hash
from app.engine.errors import FixtureError, UnsupportedChainError
from app.engine.provider import ActivityResult, BlockResult, ChainDataProvider, TransferPage
from app.engine.providers import DEFAULT_FIXTURE_ROOT, FixtureProvider
from app.engine.records import Asset, AssetKind, Chain
from app.engine.tron import usdt_trc20

FIXTURE_ID = "growjoy_tron_trc20"


@pytest.fixture
def provider() -> FixtureProvider:
    return FixtureProvider(FIXTURE_ID)


@pytest.fixture
def seed(provider: FixtureProvider) -> str:
    manifest = json.loads(
        (DEFAULT_FIXTURE_ROOT / FIXTURE_ID / "manifest.json").read_text()
    )
    return manifest["seed_address"]


def _all_transfers(provider: FixtureProvider, address: str, asset: Asset, page_size: int):
    cursor: str | None = None
    pages: list[TransferPage] = []
    while True:
        page = provider.token_transfers(
            address, asset=asset, cursor=cursor, page_size=page_size
        )
        pages.append(page)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    return pages


def test_satisfies_the_provider_protocol(provider: FixtureProvider):
    assert isinstance(provider, ChainDataProvider)
    assert provider.chain is Chain.TRON
    assert provider.name == "fixture:trongrid"


def test_latest_block_pins_the_tip(provider: FixtureProvider):
    result = provider.latest_block()
    assert isinstance(result, BlockResult)
    assert result.block.height == 65_213_001
    assert result.snapshot.tip_block == result.block


def test_missing_fixture_raises():
    with pytest.raises(FixtureError):
        FixtureProvider("does_not_exist")


def test_checksum_mismatch_raises(tmp_path: Path):
    src = DEFAULT_FIXTURE_ROOT / FIXTURE_ID
    dst = tmp_path / FIXTURE_ID
    shutil.copytree(src, dst)
    tampered = json.loads((dst / "transfers.json").read_text())
    tampered[0]["value"] = "1"
    (dst / "transfers.json").write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n")
    with pytest.raises(FixtureError, match="checksum mismatch"):
        FixtureProvider(FIXTURE_ID, root=tmp_path)


def test_wrong_chain_asset_is_rejected(provider: FixtureProvider, seed: str):
    eth_asset = Asset(
        chain=Chain.ETHEREUM, kind=AssetKind.TOKEN, symbol="USDT", decimals=6,
        contract="0xdAC17F958D2ee523a2206206994597C13D831ec7",
    )
    with pytest.raises(UnsupportedChainError):
        provider.token_transfers(seed, asset=eth_asset)


def test_seed_has_exactly_its_one_outgoing_transfer(provider: FixtureProvider, seed: str):
    page = provider.token_transfers(seed, asset=usdt_trc20())
    transfers = [t for tx in page.transactions for t in tx.transfers]
    assert len(transfers) == 1
    tr = transfers[0]
    assert tr.from_address == seed
    assert tr.value == Decimal("1499.500000")
    assert tr.value_raw == 1_499_500_000
    assert tr.snapshot_id == page.snapshot.snapshot_id
    assert page.next_cursor is None


def test_pagination_covers_every_record_once(provider: FixtureProvider):
    # "cons" touches three transfers: rot2->cons 1400, rot3->cons 800, cons->dep 2200.
    manifest = json.loads(
        (DEFAULT_FIXTURE_ROOT / FIXTURE_ID / "manifest.json").read_text()
    )
    cons = manifest["addresses"]["cons"]

    one_page = provider.token_transfers(cons, asset=usdt_trc20(), page_size=100)
    whole = [t for tx in one_page.transactions for t in tx.transfers]
    assert sorted(t.value for t in whole) == [
        Decimal("800.000000"),
        Decimal("1400.000000"),
        Decimal("2200.000000"),
    ]
    assert one_page.next_cursor is None

    paged = _all_transfers(provider, cons, usdt_trc20(), page_size=1)
    assert len(paged) == 3
    stepwise = [t for page in paged for tx in page.transactions for t in tx.transfers]
    assert [t.value for t in stepwise] == [t.value for t in whole]


def test_replay_is_deterministic(provider: FixtureProvider, seed: str):
    a = provider.token_transfers(seed, asset=usdt_trc20())
    b = FixtureProvider(FIXTURE_ID).token_transfers(seed, asset=usdt_trc20())
    assert canonical_hash(a.model_dump(mode="python")) == canonical_hash(
        b.model_dump(mode="python")
    )
    assert a.snapshot.response_checksum == b.snapshot.response_checksum


def test_address_activity_reports_contract_flag(provider: FixtureProvider):
    result = provider.address_activity(usdt_trc20().contract or "")
    assert isinstance(result, ActivityResult)
    assert result.activity.is_contract is True


def test_unknown_address_activity_is_empty_not_an_error(provider: FixtureProvider):
    result = provider.address_activity("TFczxzPhnThNSqr5by8tvxsdCFRRz6cPNq")
    assert result.activity.transfer_count == 0
    assert result.activity.first_seen is None
