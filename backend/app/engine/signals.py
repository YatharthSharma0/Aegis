"""Account-model (Tron / EVM) structural entity signals.

These are the behavioural heuristics from the design vault
(``04-Wallet-Clustering-Heuristics`` H3-H5, ``05-VASP-Attribution-Logic``
Layer 2). Account chains have no common-input-ownership signal, so entity
inference is behaviour-based: how an address receives, how fast and how
completely it forwards, to how many counterparties, and when.

Every hit records **evidence** (why it fired, in one line) and **limitations**
(how it can be wrong). Nothing here is proof — each hit is a weighted score a
human reviews.

Two kinds of hit:

* ``typology`` — a laundering-shaped pattern (peel chain, rotation, fan-in
  consolidation, rapid fan-out). Surfaced in ``TraceResult.typologies``.
* ``vasp`` — a "behaves like an exchange deposit / hot wallet" pattern
  (deposit fan-in, sweep target, batch withdrawals, high-activity service).
  Consumed by Phase 1C attribution; not a typology.

The detectors take pre-computed :class:`AddressStats`; they never touch a
provider, so they are cheap and trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.engine.result import TypologySignal


class SignalKind(StrEnum):
    TYPOLOGY = "typology"
    VASP = "vasp"


@dataclass(frozen=True)
class AddressStats:
    """Everything a detector needs about one address, from the discovered subgraph."""

    address: str
    is_seed: bool
    is_contract: bool
    total_in: Decimal
    total_out: Decimal
    distinct_senders: int
    distinct_recipients: int
    incoming_count: int
    outgoing_count: int
    # Largest single recipient's share of total_out, in [0, 1]; 0 when nothing out.
    largest_out_fraction: Decimal
    first_activity: datetime | None
    last_activity: datetime | None
    # Seconds between the last inflow and the first outflow, when positive.
    forward_latency_s: Decimal | None


@dataclass(frozen=True)
class SignalConfig:
    """Thresholds. Defaults aim at real-chain volumes; tests dial them down."""

    forward_ratio: Decimal = Decimal("0.90")     # "forwards ~everything"
    peel_dominant_fraction: Decimal = Decimal("0.90")
    rotation_max_recipients: int = 2
    fan_in_min_senders: int = 5
    fan_out_min_recipients: int = 8
    sweep_min_incoming: int = 10
    service_min_activity: int = 50
    fast_forward_s: Decimal = Decimal("900")     # 15 minutes


@dataclass(frozen=True)
class SignalHit:
    name: str
    kind: SignalKind
    score: Decimal
    address: str
    evidence: str
    limitations: str


@dataclass(frozen=True)
class SignalReport:
    hits: tuple[SignalHit, ...]

    def typologies(self) -> tuple[TypologySignal, ...]:
        seen: dict[tuple[str, str], TypologySignal] = {}
        for hit in self.hits:
            if hit.kind is not SignalKind.TYPOLOGY:
                continue
            key = (hit.name, hit.address)
            if key not in seen:
                seen[key] = TypologySignal(
                    name=hit.name, score=hit.score, model="rule", addresses=(hit.address,)
                )
        return tuple(seen.values())

    def labels_for(self, address: str) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(h.name for h in self.hits if h.address == address)
        )

    def vasp_signals_for(self, address: str) -> tuple[SignalHit, ...]:
        return tuple(
            h for h in self.hits if h.address == address and h.kind is SignalKind.VASP
        )


# --------------------------------------------------------------------------
# detectors
# --------------------------------------------------------------------------


def _ratio(part: Decimal, whole: Decimal) -> Decimal:
    return part / whole if whole > 0 else Decimal(0)


def _fast(stats: AddressStats, cfg: SignalConfig) -> bool:
    return stats.forward_latency_s is not None and stats.forward_latency_s <= cfg.fast_forward_s


def _passthrough_rotation(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    if stats.is_seed or stats.total_in <= 0 or stats.outgoing_count == 0:
        return None
    fwd = _ratio(stats.total_out, stats.total_in)
    if fwd < cfg.forward_ratio or stats.distinct_recipients > cfg.rotation_max_recipients:
        return None
    if stats.distinct_senders > cfg.fan_in_min_senders:
        return None  # that's consolidation, not a personal rotation hop
    score = min(Decimal(1), fwd) * (Decimal("1.0") if _fast(stats, cfg) else Decimal("0.8"))
    return SignalHit(
        name="passthrough_rotation",
        kind=SignalKind.TYPOLOGY,
        score=score.quantize(Decimal("0.01")),
        address=stats.address,
        evidence=(
            f"forwarded {fwd:.2%} of inflow to {stats.distinct_recipients} "
            f"address(es)"
            + (f" within {stats.forward_latency_s}s" if stats.forward_latency_s is not None else "")
        ),
        limitations="a personal wallet that promptly moves funds looks the same",
    )


def _peel_chain(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    if stats.is_seed or stats.outgoing_count < 2:
        return None
    dominant = stats.largest_out_fraction
    if dominant < cfg.peel_dominant_fraction or dominant >= 1:
        return None
    peel = Decimal(1) - dominant
    return SignalHit(
        name="peel_chain",
        kind=SignalKind.TYPOLOGY,
        score=dominant.quantize(Decimal("0.01")),
        address=stats.address,
        evidence=(
            f"{dominant:.1%} forwarded to one address, {peel:.1%} peeled across "
            f"{stats.outgoing_count - 1} other output(s)"
        ),
        limitations="a large payment plus change has the same shape once",
    )


def _rapid_fan_out(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    if stats.distinct_recipients < cfg.fan_out_min_recipients:
        return None
    score = min(Decimal(1), Decimal(stats.distinct_recipients) / (cfg.fan_out_min_recipients * 3))
    return SignalHit(
        name="rapid_fan_out",
        kind=SignalKind.TYPOLOGY,
        score=score.quantize(Decimal("0.01")),
        address=stats.address,
        evidence=f"sent to {stats.distinct_recipients} distinct recipients",
        limitations="a payroll / airdrop / batch payer fans out the same way",
    )


def _consolidation_fan_in(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    if stats.distinct_senders < cfg.fan_in_min_senders or stats.distinct_recipients > 2:
        return None
    score = min(Decimal(1), Decimal(stats.distinct_senders) / (cfg.fan_in_min_senders * 3))
    return SignalHit(
        name="fan_in_consolidation",
        kind=SignalKind.TYPOLOGY,
        score=score.quantize(Decimal("0.01")),
        address=stats.address,
        evidence=(
            f"received from {stats.distinct_senders} distinct senders, "
            f"forwarding to {stats.distinct_recipients}"
        ),
        limitations="an exchange sweep target has the same in-shape (see vasp signals)",
    )


def _deposit_fan_in(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    if stats.is_seed or stats.is_contract:
        return None
    if (
        stats.distinct_senders < cfg.fan_in_min_senders
        or stats.distinct_recipients != 1
        or stats.largest_out_fraction < Decimal("0.95")
        or not _fast(stats, cfg)
    ):
        return None
    return SignalHit(
        name="deposit_fan_in",
        kind=SignalKind.VASP,
        score=Decimal("0.7"),
        address=stats.address,
        evidence=(
            f"{stats.distinct_senders} unrelated senders, then "
            f"{stats.largest_out_fraction:.1%} swept to one target fast"
        ),
        limitations="account-abstraction / smart wallets can mimic this; not confirmation",
    )


def _sweep_target(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    if stats.is_seed or stats.is_contract:
        return None
    if (
        stats.incoming_count < cfg.sweep_min_incoming
        or stats.distinct_senders < cfg.fan_in_min_senders
    ):
        return None
    return SignalHit(
        name="sweep_target",
        kind=SignalKind.VASP,
        score=Decimal("0.65"),
        address=stats.address,
        evidence=(
            f"high in-degree ({stats.incoming_count} inflows from "
            f"{stats.distinct_senders} senders) consistent with a hot wallet"
        ),
        limitations="high in-degree alone is weak; corroborate with deposit fan-in upstream",
    )


def _batch_withdrawals(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    if stats.is_seed or stats.distinct_recipients < cfg.fan_out_min_recipients:
        return None
    return SignalHit(
        name="batch_withdrawals",
        kind=SignalKind.VASP,
        score=Decimal("0.55"),
        address=stats.address,
        evidence=f"pays out to {stats.distinct_recipients} distinct recipients",
        limitations="indistinguishable on-chain from any other batch payer",
    )


def _high_activity_service(stats: AddressStats, cfg: SignalConfig) -> SignalHit | None:
    activity = stats.incoming_count + stats.outgoing_count
    if stats.is_seed or activity < cfg.service_min_activity:
        return None
    return SignalHit(
        name="high_activity_service",
        kind=SignalKind.VASP,
        score=Decimal("0.4"),
        address=stats.address,
        evidence=f"{activity} transfers on this address — operational, not personal",
        limitations="a busy DeFi user or bot also has high activity",
    )


_DETECTORS = (
    _passthrough_rotation,
    _peel_chain,
    _rapid_fan_out,
    _consolidation_fan_in,
    _deposit_fan_in,
    _sweep_target,
    _batch_withdrawals,
    _high_activity_service,
)


def detect_account_signals(
    stats: list[AddressStats], *, config: SignalConfig | None = None
) -> SignalReport:
    """Run every detector over every address; return the collected hits."""
    cfg = config or SignalConfig()
    hits: list[SignalHit] = []
    for address_stats in sorted(stats, key=lambda s: s.address):
        for detector in _DETECTORS:
            hit = detector(address_stats, cfg)
            if hit is not None:
                hits.append(hit)
    return SignalReport(hits=tuple(hits))
