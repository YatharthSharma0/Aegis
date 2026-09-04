"""forward_trace: haircut taint, budgets, trail events, determinism."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.engine.canonical import sha256_hex
from app.engine.errors import PartialReason, TrailLostReason
from app.engine.provider import ActivityResult, BlockResult, ChainDataProvider, TransferPage
from app.engine.providers import FixtureProvider
from app.engine.providers.fixture import DEFAULT_FIXTURE_ROOT
from app.engine.records import (
    AddressActivity,
    BlockRef,
    Chain,
    NormalizedTransaction,
    ProviderSnapshot,
    Transfer,
    TxStatus,
)
from app.engine.result import TraceParams, TraceStatus
from app.engine.tron import usdt_trc20
from app.engine.walk import forward_trace

FIXTURE_ID = "growjoy_tron_trc20"
TS = datetime(2026, 8, 15, 3, 0, tzinfo=UTC)


# --------------------------------------------------------------------------
# A tiny in-memory provider for shapes the fixture doesn't cover.
# --------------------------------------------------------------------------


class StubProvider:
    name = "stub"
    chain = Chain.TRON

    def __init__(self, transfers: list[tuple[str, str, str]]) -> None:
        self._asset = usdt_trc20()
        self._transfers: list[Transfer] = []
        for i, (frm, to, amount) in enumerate(transfers):
            dec = Decimal(amount)
            self._transfers.append(
                Transfer(
                    asset=self._asset, from_address=frm, to_address=to,
                    value=dec, value_raw=int(dec.scaleb(6)),
                    tx_hash="0x" + f"{i:064x}", log_index=0,
                    block_height=100 + i, block_hash="0x" + f"{i:064x}",
                    timestamp=TS + timedelta(minutes=i), snapshot_id="stub:0",
                )
            )

    def _snap(self, suffix: str, count: int) -> ProviderSnapshot:
        tip = BlockRef(chain=Chain.TRON, height=999, block_hash="0x" + "0" * 64, timestamp=TS)
        return ProviderSnapshot(
            snapshot_id=f"stub:{suffix}", provider="stub", chain=Chain.TRON,
            endpoint="stub", captured_at=TS, tip_block=tip,
            response_checksum=sha256_hex(suffix.encode()), record_count=count,
        )

    def latest_block(self) -> BlockResult:
        tip = BlockRef(chain=Chain.TRON, height=999, block_hash="0x" + "0" * 64, timestamp=TS)
        return BlockResult(block=tip, snapshot=self._snap("tip", 1))

    def token_transfers(  # noqa: PLR0913 — mirrors the provider interface
        self, address, *, asset, cursor=None, page_size=100,
        start_block=None, end_block=None,
    ) -> TransferPage:
        hits = [t for t in self._transfers if address in (t.from_address, t.to_address)]
        snap = self._snap(f"trc20:{address}", len(hits))
        txs = tuple(
            NormalizedTransaction(
                chain=Chain.TRON, tx_hash=t.tx_hash, status=TxStatus.SUCCESS,
                block=BlockRef(chain=Chain.TRON, height=t.block_height,
                               block_hash=t.block_hash, timestamp=t.timestamp),
                from_address=t.from_address,
                transfers=(t.model_copy(update={"snapshot_id": snap.snapshot_id}),),
                snapshot_id=snap.snapshot_id,
            )
            for t in hits
        )
        return TransferPage(transactions=txs, snapshot=snap, next_cursor=None)

    def address_activity(self, address) -> ActivityResult:
        return ActivityResult(
            activity=AddressActivity(
                chain=Chain.TRON, address=address, is_contract=False,
                transfer_count=0, snapshot_id=f"stub:activity:{address}",
            ),
            snapshot=self._snap(f"activity:{address}", 0),
        )


def test_stub_satisfies_protocol():
    assert isinstance(StubProvider([]), ChainDataProvider)


# --------------------------------------------------------------------------
# Fixture-based
# --------------------------------------------------------------------------


@pytest.fixture
def provider() -> FixtureProvider:
    return FixtureProvider(FIXTURE_ID)


def _edges_by_pair(inv):
    return {(e.from_address, e.to_address): e for e in inv.result.graph_edges}


def test_growjoy_trace_haircut(provider: FixtureProvider):
    inv = forward_trace(
        provider.seed_address, chain=Chain.TRON, asset=usdt_trc20(), provider=provider
    )
    assert inv.status is TraceStatus.DONE
    assert inv.block_heights == {Chain.TRON: 65_213_001}

    addr = json_addresses()
    edges = _edges_by_pair(inv)
    assert edges[(addr["seed"], addr["rot1"])].taint == Decimal("1")
    assert edges[(addr["rot2"], addr["cons"])].taint == Decimal("1")
    # cons receives 1400 tainted but 2200 total in (rot3's 800 is clean) -> haircut
    assert edges[(addr["cons"], addr["dep"])].taint == Decimal("0.636363636364")
    assert edges[(addr["dep"], addr["exch_hot"])].taint == Decimal("0.636363636364")

    # every graph edge links back to a snapshot
    for edge in inv.result.graph_edges:
        assert edge.evidence.snapshot_id
        assert edge.evidence.tx_hash == edge.tx_hash


def test_trace_is_deterministic(provider: FixtureProvider):
    a = forward_trace(provider.seed_address, chain=Chain.TRON, asset=usdt_trc20(),
                      provider=provider)
    b = forward_trace(provider.seed_address, chain=Chain.TRON, asset=usdt_trc20(),
                      provider=FixtureProvider(FIXTURE_ID))
    assert a.result_hash() == b.result_hash()


def test_taint_is_conserved_along_every_path(provider: FixtureProvider):
    inv = forward_trace(provider.seed_address, chain=Chain.TRON, asset=usdt_trc20(),
                        provider=provider)
    tol = Decimal("0.00001")
    seed = provider.seed_address
    tainted_in: dict[str, Decimal] = {}
    tainted_out: dict[str, Decimal] = {}
    for e in inv.result.graph_edges:
        amt = e.value * e.taint
        assert 0 <= amt <= e.value  # never exceeds the transfer
        tainted_out[e.from_address] = tainted_out.get(e.from_address, Decimal(0)) + amt
        tainted_in[e.to_address] = tainted_in.get(e.to_address, Decimal(0)) + amt
    for addr, out_amt in tainted_out.items():
        supply = tainted_in.get(addr, Decimal(0))
        if addr == seed:
            continue
        assert out_amt <= supply + tol


def test_max_hops_stops_the_branch(provider: FixtureProvider):
    inv = forward_trace(
        provider.seed_address, chain=Chain.TRON, asset=usdt_trc20(), provider=provider,
        params=TraceParams(max_hops=2),
    )
    assert inv.status is TraceStatus.DONE  # per-branch stop, not partial
    reasons = {ev.reason for ev in inv.result.trail_events}
    assert TrailLostReason.MAX_HOPS in reasons


def test_mixer_address_stops_and_reports_amount(provider: FixtureProvider):
    addr = json_addresses()
    inv = forward_trace(
        provider.seed_address, chain=Chain.TRON, asset=usdt_trc20(), provider=provider,
        mixer_addresses=frozenset({addr["cons"]}),
    )
    mixer_events = [e for e in inv.result.trail_events if e.reason is TrailLostReason.MIXER_LIKE]
    assert len(mixer_events) == 1
    assert mixer_events[0].address == addr["cons"]
    assert mixer_events[0].amount == Decimal("1400.000000")
    assert (addr["cons"], addr["dep"]) not in _edges_by_pair(inv)


def test_node_budget_makes_it_partial(provider: FixtureProvider):
    inv = forward_trace(
        provider.seed_address, chain=Chain.TRON, asset=usdt_trc20(), provider=provider,
        params=TraceParams(max_nodes=3),
    )
    assert inv.status is TraceStatus.PARTIAL
    assert inv.partial_reason is PartialReason.NODE_BUDGET


# --------------------------------------------------------------------------
# Stub-based: shapes the fixture doesn't have
# --------------------------------------------------------------------------


def test_clean_fan_in_dilutes_but_tainted_fan_in_accumulates():
    # A -> B (victim 100), C -> B (clean 100), B -> D (200). Half of D is tainted.
    stub = StubProvider([("A", "B", "100"), ("C", "B", "100"), ("B", "D", "200")])
    inv = forward_trace("A", chain=Chain.TRON, asset=usdt_trc20(), provider=stub)
    edge = _edges_by_pair(inv)[("B", "D")]
    assert edge.taint == Decimal("0.5")


def test_cycle_edge_is_dropped_from_propagation():
    stub = StubProvider([("A", "B", "100"), ("B", "C", "100"), ("C", "A", "100")])
    inv = forward_trace("A", chain=Chain.TRON, asset=usdt_trc20(), provider=stub)
    reasons = {e.reason for e in inv.result.trail_events}
    assert TrailLostReason.CYCLE in reasons
    # the back-edge C->A carries no forward taint
    assert ("C", "A") not in _edges_by_pair(inv)


def test_min_value_prunes_a_dust_peel():
    stub = StubProvider([("A", "B", "1000"), ("B", "C", "995"), ("B", "dust", "5")])
    inv = forward_trace(
        "A", chain=Chain.TRON, asset=usdt_trc20(), provider=stub,
        params=TraceParams(min_value=Decimal("10")),
    )
    reasons = {e.reason for e in inv.result.trail_events}
    assert TrailLostReason.MIN_VALUE in reasons
    assert ("B", "dust") not in _edges_by_pair(inv)


# --------------------------------------------------------------------------


def json_addresses() -> dict[str, str]:
    return json.loads(
        (DEFAULT_FIXTURE_ROOT / FIXTURE_ID / "manifest.json").read_text()
    )["addresses"]
