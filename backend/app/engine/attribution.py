"""Two-tier VASP attribution with a transparent confidence formula.

The question SIH26183 actually asks: *which exchange received the traced funds?*
— answered without any exchange customer records.

* **Layer 1 — dataset-confirmed.** The reached address matches a VASP label in a
  loaded :class:`LabelSet`. ``verified`` (``tier = dataset_confirmed``), a real
  name, high source score.
* **Layer 2 — heuristic.** No label, but the address *behaves* like an exchange
  deposit / hot wallet (the ``vasp``-kind signals from :mod:`app.engine.signals`).
  ``tier = heuristic``, name stays ``None`` → "Unidentified VASP-like endpoint".
* Conflicting labels → ``tier = conflict``, name ``None``, the clashing names
  surfaced. Never silently pick one.
* Sanctions labels are attached as evidence, never as a VASP name.

The confidence formula (default weights from ``05-VASP-Attribution-Logic``):

    confidence = w1 * source_score + w2 * path_directness + w3 * taint_retained
               + w4 * corroboration - p1 * mixer_on_path - p2 * bridge_uncertainty
    clamped to [0, 1]

Every term and weight is carried in :class:`ConfidenceTerms` so a report can
print the arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.engine.labels import LabelSet, LabelType
from app.engine.records import Chain
from app.engine.result import (
    AttributionTier,
    ConfidenceTerms,
    EvidenceRef,
    VaspCandidate,
)
from app.engine.signals import SignalHit

CORROBORATION_CAP = 3
HEURISTIC_SOURCE_CAP = Decimal("0.7")
_QUANT = Decimal("0.0001")


@dataclass(frozen=True)
class ConfidenceWeights:
    w1_source: Decimal = Decimal("0.45")
    w2_directness: Decimal = Decimal("0.15")
    w3_taint: Decimal = Decimal("0.20")
    w4_corroboration: Decimal = Decimal("0.20")
    p1_mixer: Decimal = Decimal("0.25")
    p2_bridge: Decimal = Decimal("0.10")


DEFAULT_WEIGHTS = ConfidenceWeights()


@dataclass(frozen=True)
class EndpointContext:
    """One address the trace reached that might be an off-ramp."""

    address: str
    chain: Chain
    hops_from_seed: int
    taint_retained: Decimal              # victim funds here / total victim outflow, [0,1]
    reaching_paths: int
    mixer_on_path: bool
    bridge_hops: int
    deposit_address: str | None
    is_sink: bool
    vasp_signals: tuple[SignalHit, ...] = ()
    cluster_addresses: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)


_TIER_ORDER = {
    AttributionTier.DATASET_CONFIRMED: 0,
    AttributionTier.HEURISTIC: 1,
    AttributionTier.SANCTIONS: 2,
    AttributionTier.UNKNOWN: 3,
    AttributionTier.CONFLICT: 4,
}


def attribute(
    endpoints: list[EndpointContext],
    labels: LabelSet | None,
    *,
    weights: ConfidenceWeights = DEFAULT_WEIGHTS,
) -> tuple[VaspCandidate, ...]:
    """Score every endpoint; return ranked candidates (nearest confirmed first)."""
    scored: list[tuple[int, int, Decimal, VaspCandidate]] = []
    for ctx in endpoints:
        base = _classify(ctx, labels)
        if base is None:
            continue
        tier, source_score, name, label, sig_names = base
        confidence, terms = _confidence(ctx, source_score, weights)
        candidate = VaspCandidate(
            rank=1,  # replaced after sorting
            tier=tier,
            source=_source_label(tier, ctx, labels),
            confidence=confidence,
            name=name,
            label=label,
            confidence_terms=terms,
            deposit_address=ctx.deposit_address,
            reaching_paths=max(1, ctx.reaching_paths),
            hops_from_seed=ctx.hops_from_seed,
            signals=sig_names,
            evidence=ctx.evidence,
        )
        scored.append((_TIER_ORDER[tier], ctx.hops_from_seed, -confidence, candidate))

    scored.sort(key=lambda row: (row[0], row[1], row[2]))
    return tuple(
        candidate.model_copy(update={"rank": i})
        for i, (_, _, _, candidate) in enumerate(scored, start=1)
    )


def _classify(
    ctx: EndpointContext, labels: LabelSet | None
) -> tuple[AttributionTier, Decimal, str | None, str | None, tuple[str, ...]] | None:
    sanction_names: tuple[str, ...] = ()
    if labels is not None:
        sanctions = labels.lookup(ctx.address, ctx.chain, types=[LabelType.SANCTIONS])
        sanction_names = tuple(
            f"ofac_sanctioned:{s.entity_name or 'unnamed'}" for s in sanctions
        )
        vasp_here = labels.lookup(
            ctx.address, ctx.chain, types=[LabelType.VASP, LabelType.SERVICE]
        )
        names = {label.entity_name for label in vasp_here if label.entity_name}
        if len(names) > 1:
            return (
                AttributionTier.CONFLICT,
                Decimal("0.5"),
                None,
                "conflicting attributions: " + ", ".join(sorted(names)),
                sanction_names + tuple(f"claims:{n}" for n in sorted(names)),
            )
        if vasp_here:
            return (
                AttributionTier.DATASET_CONFIRMED,
                Decimal("1.0"),
                next(iter(names), None),
                None,
                sanction_names,
            )
        via_cluster = _cluster_label(ctx, labels)
        if via_cluster is not None:
            return (
                AttributionTier.DATASET_CONFIRMED,
                Decimal("0.85"),
                via_cluster,
                None,
                (*sanction_names, "attributed_via_cluster"),
            )

    if ctx.vasp_signals:
        score = min(
            HEURISTIC_SOURCE_CAP,
            sum((h.score for h in ctx.vasp_signals), Decimal(0)) / 2,
        )
        return (
            AttributionTier.HEURISTIC,
            score,
            None,
            "Unidentified VASP-like endpoint",
            sanction_names + tuple(h.name for h in ctx.vasp_signals),
        )

    if ctx.is_sink:
        return (
            AttributionTier.UNKNOWN,
            Decimal("0.0"),
            None,
            "No VASP identified within trace bounds",
            sanction_names,
        )
    return None


def _cluster_label(ctx: EndpointContext, labels: LabelSet) -> str | None:
    for address in ctx.cluster_addresses:
        matched = labels.lookup(
            address, ctx.chain, types=[LabelType.VASP, LabelType.SERVICE]
        )
        for label in matched:
            if label.entity_name:
                return label.entity_name
    return None


def _confidence(
    ctx: EndpointContext, source_score: Decimal, w: ConfidenceWeights
) -> tuple[Decimal, ConfidenceTerms]:
    directness = Decimal(1) / (Decimal(1) + Decimal(ctx.hops_from_seed))
    corroboration = min(
        Decimal(1), Decimal(ctx.reaching_paths) / Decimal(CORROBORATION_CAP)
    )
    mixer = Decimal(1) if ctx.mixer_on_path else Decimal(0)
    bridge = min(Decimal(1), Decimal(ctx.bridge_hops) / Decimal(3))
    taint = min(Decimal(1), max(Decimal(0), ctx.taint_retained))

    terms = {
        "source_score": source_score.quantize(_QUANT),
        "path_directness": directness.quantize(_QUANT),
        "taint_retained": taint.quantize(_QUANT),
        "corroboration": corroboration.quantize(_QUANT),
        "mixer_on_path": mixer,
        "bridge_uncertainty": bridge.quantize(_QUANT),
    }
    weight_map = {
        "source_score": w.w1_source,
        "path_directness": w.w2_directness,
        "taint_retained": w.w3_taint,
        "corroboration": w.w4_corroboration,
        "mixer_on_path": -w.p1_mixer,
        "bridge_uncertainty": -w.p2_bridge,
    }
    raw = sum((terms[k] * weight_map[k] for k in terms), Decimal(0))
    score = min(Decimal(1), max(Decimal(0), raw)).quantize(_QUANT)
    return score, ConfidenceTerms(terms=terms, weights=weight_map, score=score)


def _source_label(
    tier: AttributionTier, ctx: EndpointContext, labels: LabelSet | None
) -> str:
    if tier is AttributionTier.DATASET_CONFIRMED and labels is not None:
        hits = labels.lookup(
            ctx.address, ctx.chain, types=[LabelType.VASP, LabelType.SERVICE]
        )
        if hits:
            return hits[0].pack_id
        return "label-pack (via cluster)"
    if tier is AttributionTier.CONFLICT:
        return "conflicting label packs"
    return "heuristic"
