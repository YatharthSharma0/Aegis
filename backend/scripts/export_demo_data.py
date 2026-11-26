"""Generate the frontend's offline demo data by running the real engine.

    uv run python scripts/export_demo_data.py

Every scenario is **synthetic**: fictional addresses, entities and amounts. Each
one is traced by ``forward_trace`` and serialised through the same wire schemas
and report builder the API uses, so the demo screens show real engine output in
the real response shapes. Output is deterministic.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.reports import build_report
from app.domain.schemas import TraceGraphResponse, TraceStatusResponse
from app.domain.store import InvestigationRecord
from app.engine.canonical import sha256_hex
from app.engine.labels import Label, LabelPack, LabelSet, LabelType
from app.engine.provider import ActivityResult, BlockResult, ChainDataProvider, TransferPage
from app.engine.providers import FixtureProvider
from app.engine.records import (
    AddressActivity,
    BlockRef,
    Chain,
    NormalizedTransaction,
    ProviderSnapshot,
    Transfer,
    TxStatus,
)
from app.engine.result import TraceParams
from app.engine.tron import usdt_trc20
from app.engine.walk import forward_trace

_REPO = Path(__file__).resolve().parents[2]
OUTPUT = _REPO / "frontend" / "src" / "demo" / "data" / "scenarios.json"

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_FIRST_BLOCK = 65_300_000


def address(label: str) -> str:
    """A base58check-valid Tron address that belongs to nobody."""
    payload = b"\x41" + hashlib.sha256(f"aegis-demo-{label}".encode()).digest()[:20]
    raw = payload + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    num, out = int.from_bytes(raw, "big"), ""
    while num:
        num, rem = divmod(num, 58)
        out = _B58[rem] + out
    return out


def _hash(text: str) -> str:
    return "0x" + hashlib.sha256(text.encode()).hexdigest()


# (from, to, USDT amount, minutes after the scenario start)
Flow = tuple[str, str, str, int]


class SyntheticProvider:
    """Serves one scenario's hand-written transfers as a ``ChainDataProvider``."""

    name = "demo:synthetic"
    chain = Chain.TRON

    def __init__(self, key: str, start: datetime, flows: list[Flow]) -> None:
        self._start = start
        asset = usdt_trc20()
        self._transfers = [
            Transfer(
                asset=asset,
                from_address=address(f"{key}-{frm}"),
                to_address=address(f"{key}-{to}"),
                value=Decimal(amount),
                value_raw=int(Decimal(amount).scaleb(asset.decimals)),
                tx_hash=_hash(f"{key}-tx-{i}"),
                log_index=0,
                block_height=_FIRST_BLOCK + minute * 20,
                block_hash=_hash(f"{key}-block-{minute}"),
                timestamp=start + timedelta(minutes=minute),
                snapshot_id="pending",
            )
            for i, (frm, to, amount, minute) in enumerate(flows)
        ]
        last = max(t.block_height for t in self._transfers)
        self._tip = BlockRef(
            chain=Chain.TRON,
            height=last + 100,
            block_hash=_hash(f"{key}-tip"),
            timestamp=start + timedelta(days=1),
        )
        self._key = key

    def _snapshot(self, suffix: str, count: int) -> ProviderSnapshot:
        return ProviderSnapshot(
            snapshot_id=f"demo:{self._key}:{suffix}",
            provider=self.name,
            chain=Chain.TRON,
            endpoint=f"synthetic/{suffix.split(':', maxsplit=1)[0]}",
            captured_at=self._start + timedelta(days=1),
            tip_block=self._tip,
            response_checksum=sha256_hex(f"{self._key}:{suffix}:{count}".encode()),
            record_count=count,
            notes="SYNTHETIC demo data - not read from any blockchain",
        )

    def latest_block(self) -> BlockResult:
        return BlockResult(block=self._tip, snapshot=self._snapshot("tip", 1))

    def token_transfers(self, address: str, **_: Any) -> TransferPage:
        hits = [t for t in self._transfers if address in (t.from_address, t.to_address)]
        snapshot = self._snapshot(f"trc20:{address}", len(hits))
        transactions = tuple(
            NormalizedTransaction(
                chain=Chain.TRON,
                tx_hash=t.tx_hash,
                status=TxStatus.SUCCESS,
                block=BlockRef(
                    chain=Chain.TRON,
                    height=t.block_height,
                    block_hash=t.block_hash,
                    timestamp=t.timestamp,
                ),
                from_address=t.from_address,
                transfers=(t.model_copy(update={"snapshot_id": snapshot.snapshot_id}),),
                snapshot_id=snapshot.snapshot_id,
            )
            for t in hits
        )
        return TransferPage(transactions=transactions, snapshot=snapshot, next_cursor=None)

    def address_activity(self, address: str) -> ActivityResult:
        return ActivityResult(
            activity=AddressActivity(
                chain=Chain.TRON,
                address=address,
                is_contract=False,
                transfer_count=0,
                snapshot_id=f"demo:{self._key}:activity:{address}",
            ),
            snapshot=self._snapshot(f"activity:{address}", 0),
        )


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    description: str
    day: int  # day of August 2026
    flows: list[Flow]
    labels: tuple[tuple[str, LabelType, str], ...] = ()
    params: TraceParams | None = None


SCENARIOS = [
    Scenario(
        key="investment",
        title="Fake investment platform",
        description="Layered through three wallets with a side peel, into a labelled exchange.",
        day=3,
        flows=[
            ("seed", "w1", "25000", 0),
            ("w1", "w2", "25000", 6),
            ("w2", "w3", "23200", 11),
            ("w2", "peel", "1800", 12),
            ("other", "w3", "6800", 14),
            ("w3", "deposit", "30000", 19),
            ("deposit", "hot", "30000", 31),
        ],
        labels=(("hot", LabelType.VASP, "SampleCoin Exchange"),),
    ),
    Scenario(
        key="digital_arrest",
        title="Digital-arrest extortion",
        description="Wide fan-out to mule wallets, regrouped and cashed out at two exchanges.",
        day=7,
        flows=[
            *[("seed", f"mule{i}", "6000", i) for i in range(1, 9)],
            *[(f"mule{i}", "pool_a", "6000", 20 + i) for i in range(1, 6)],
            *[(f"mule{i}", "pool_b", "6000", 30 + i) for i in range(6, 9)],
            ("pool_a", "dep_a", "30000", 41),
            ("pool_b", "dep_b", "18000", 44),
            ("dep_a", "hot_a", "30000", 52),
            ("dep_b", "hot_b", "18000", 57),
        ],
        labels=(
            ("hot_a", LabelType.VASP, "DemoExchange"),
            ("hot_b", LabelType.VASP, "Example OTC Desk"),
        ),
    ),
    Scenario(
        key="heuristic",
        title="Loan-app fraud",
        description="Ends at an unlabelled wallet that behaves like an exchange deposit address.",
        day=11,
        flows=[
            ("seed", "hop1", "4200", 0),
            ("hop1", "hop2", "4200", 8),
            *[(f"user{i}", "collector", str(900 + i * 150), 10 + i) for i in range(1, 7)],
            ("hop2", "collector", "4200", 22),
            ("collector", "treasury", "12750", 27),
        ],
    ),
    Scenario(
        key="bridge",
        title="Phishing wallet drain",
        description="Most funds leave through a cross-chain bridge, where the trail stops.",
        day=14,
        flows=[
            ("seed", "drainer", "18500", 0),
            ("drainer", "splitter", "18500", 3),
            ("splitter", "bridge", "15000", 7),
            ("splitter", "holding", "3500", 9),
        ],
        labels=(("bridge", LabelType.BRIDGE, "DemoSwap Bridge"),),
    ),
    Scenario(
        key="conflict",
        title="P2P merchant scam",
        description="Two label sources name different operators for the same endpoint.",
        day=18,
        flows=[
            ("seed", "broker", "9600", 0),
            ("broker", "endpoint", "9600", 15),
        ],
        labels=(
            ("endpoint", LabelType.VASP, "SampleCoin Exchange"),
            ("endpoint", LabelType.VASP, "Example OTC Desk"),
        ),
    ),
    Scenario(
        key="watchlist",
        title="Ransom payment",
        description="Funds still resting in an unattributed wallet that is on a sample watchlist.",
        day=21,
        flows=[
            ("seed", "relay", "52000", 0),
            ("relay", "resting", "52000", 45),
        ],
        labels=(("resting", LabelType.SANCTIONS, "Sample Watchlist Entry"),),
    ),
    Scenario(
        key="partial",
        title="Long layering chain",
        description="The walk hits its node budget, so the result is marked partial.",
        day=24,
        flows=[
            ("seed", "l1", "7400", 0),
            *[(f"l{i}", f"l{i + 1}", "7400", i * 4) for i in range(1, 9)],
        ],
        params=TraceParams(max_nodes=5),
    ),
]


def _label_set(scenario: Scenario) -> LabelSet:
    labels = tuple(
        Label(
            address=address(f"{scenario.key}-{node}"),
            chain=Chain.TRON,
            label_type=label_type,
            entity_name=name,
            category="synthetic_demo",
            pack_id="synthetic_demo_labels",
            source="synthetic",
            last_verified=date(2026, 8, 20),
        )
        for node, label_type, name in scenario.labels
    )
    # LabelSet only reads ``labels`` from a pack, so an in-memory one is enough.
    pack: LabelPack = SimpleNamespace(labels=labels, meta=None)  # type: ignore[assignment]
    return LabelSet([pack])


def _export(  # noqa: PLR0913, PLR0917 — one argument per scenario field
    key: str,
    title: str,
    description: str,
    start: datetime,
    seed: str,
    provider: ChainDataProvider,
    labels: LabelSet,
    params: TraceParams | None,
) -> dict[str, Any]:
    investigation = forward_trace(
        seed,
        chain=Chain.TRON,
        asset=usdt_trc20(),
        provider=provider,
        labels=labels,
        params=params,
    )
    created = start + timedelta(days=1)
    finished = created + timedelta(seconds=4)
    investigation = investigation.model_copy(
        update={"started_at": created, "finished_at": finished}
    )
    record = InvestigationRecord(
        trace_id=f"demo-{key}",
        case_id=None,
        start_address=seed,
        chain=Chain.TRON,
        params=investigation.params,
        status=investigation.status,
        created_at=created,
        started_at=created,
        finished_at=finished,
        investigation=investigation,
    )
    report = build_report(record, generated_by=None)
    stamp = finished.isoformat()
    report["header"]["generated_at"] = stamp
    report["certification"]["generated_at"] = stamp
    return {
        "key": key,
        "title": title,
        "description": description,
        "seed": seed,
        "trace": TraceStatusResponse.of(record).model_dump(mode="json", by_alias=True),
        "graph": TraceGraphResponse.of(record).model_dump(mode="json", by_alias=True),
        "report": report,
    }


def build() -> list[dict[str, Any]]:
    fixture = FixtureProvider("growjoy_tron_trc20")
    out = [
        _export(
            "task_scam",
            "Part-time task scam",
            "A mixer peel on the way to a labelled exchange hot wallet.",
            datetime(2026, 8, 15, 3, 0, tzinfo=UTC),
            fixture.seed_address,
            fixture,
            LabelSet.from_pack_ids(["aegis_demo_pack"]),
            None,
        )
    ]
    for s in SCENARIOS:
        start = datetime(2026, 8, s.day, 5, 30, tzinfo=UTC)
        out.append(
            _export(
                s.key,
                s.title,
                s.description,
                start,
                address(f"{s.key}-seed"),
                SyntheticProvider(s.key, start, s.flows),
                _label_set(s),
                s.params,
            )
        )
    return out


def render() -> str:
    return json.dumps(build(), indent=1, sort_keys=True) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
