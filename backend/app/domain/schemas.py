"""API request/response shapes for the trace endpoints (per ``05-API-Contracts``).

Deliberately separate from :mod:`app.engine.result`: the engine types are the
internal contract, these are the wire contract. ``from_*`` classmethods map one
to the other so the two can evolve independently.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.store import InvestigationRecord
from app.engine.records import Chain
from app.engine.result import (
    EvidenceRef,
    GraphEdge,
    GraphNode,
    Investigation,
    TaintModel,
    TraceParams,
    TraceStatus,
    TypologySignal,
    VaspCandidate,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- request -----------------------------------------------------------------


class TraceParamsIn(_Model):
    max_hops: int = Field(default=8, ge=1, le=64)
    min_value: Decimal = Field(default=Decimal("10"), ge=0)
    min_taint: Decimal = Field(default=Decimal("0.01"), ge=0, le=1)
    taint_model: TaintModel = TaintModel.HAIRCUT

    def to_engine(self) -> TraceParams:
        return TraceParams(
            max_hops=self.max_hops,
            min_value=self.min_value,
            min_taint=self.min_taint,
            taint_model=self.taint_model,
        )


class TraceRequest(_Model):
    address: str = Field(min_length=1)
    case_id: str | None = None
    chain: Chain = Chain.TRON
    params: TraceParamsIn = Field(default_factory=TraceParamsIn)


# --- response --------------------------------------------------------------


class TraceAccepted(_Model):
    trace_id: str
    status: TraceStatus
    stream_url: str


class EvidenceOut(_Model):
    provider: str
    snapshot_id: str
    tx_hash: str | None = None
    block_height: int | None = None
    block_hash: str | None = None
    captured_at: datetime | None = None

    @classmethod
    def of(cls, ref: EvidenceRef) -> EvidenceOut:
        return cls(
            provider=ref.provider,
            snapshot_id=ref.snapshot_id,
            tx_hash=ref.tx_hash,
            block_height=ref.block_height,
            block_hash=ref.block_hash,
            captured_at=ref.captured_at,
        )


class VaspCandidateOut(_Model):
    rank: int
    tier: str
    verified: bool
    source: str
    confidence: Decimal
    name: str | None
    label: str | None
    deposit_address: str | None
    hops_from_seed: int
    reaching_paths: int
    signals: list[str]
    confidence_terms: dict[str, Decimal] | None
    confidence_weights: dict[str, Decimal] | None
    evidence: list[EvidenceOut]

    @classmethod
    def of(cls, c: VaspCandidate) -> VaspCandidateOut:
        return cls(
            rank=c.rank,
            tier=c.tier.value,
            verified=c.tier.value == "dataset_confirmed",
            source=c.source,
            confidence=c.confidence,
            name=c.name,
            label=c.label,
            deposit_address=c.deposit_address,
            hops_from_seed=c.hops_from_seed,
            reaching_paths=c.reaching_paths,
            signals=list(c.signals),
            confidence_terms=dict(c.confidence_terms.terms) if c.confidence_terms else None,
            confidence_weights=(
                dict(c.confidence_terms.weights) if c.confidence_terms else None
            ),
            evidence=[EvidenceOut.of(e) for e in c.evidence],
        )


class TypologyOut(_Model):
    name: str
    score: Decimal
    model: str
    addresses: list[str]

    @classmethod
    def of(cls, t: TypologySignal) -> TypologyOut:
        return cls(name=t.name, score=t.score, model=t.model, addresses=list(t.addresses))


class TrailEventOut(_Model):
    reason: str
    address: str | None
    asset_symbol: str | None
    amount: Decimal | None
    timestamp: datetime | None


class TraceResultOut(_Model):
    summary: str
    vasp_candidates: list[VaspCandidateOut]
    typologies: list[TypologyOut]
    trail_events: list[TrailEventOut]

    @classmethod
    def of(cls, inv: Investigation) -> TraceResultOut | None:
        if inv.result is None:
            return None
        r = inv.result
        return cls(
            summary=r.summary,
            vasp_candidates=[VaspCandidateOut.of(c) for c in r.vasp_candidates],
            typologies=[TypologyOut.of(t) for t in r.typologies],
            trail_events=[
                TrailEventOut(
                    reason=e.reason.value,
                    address=e.address,
                    asset_symbol=e.asset_symbol,
                    amount=e.amount,
                    timestamp=e.timestamp,
                )
                for e in r.trail_events
            ],
        )


class TraceStatusResponse(_Model):
    trace_id: str
    case_id: str | None
    start_address: str
    chain: Chain
    status: TraceStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    block_heights: dict[str, int]
    result_hash: str | None
    result: TraceResultOut | None
    error: str | None

    @classmethod
    def of(cls, rec: InvestigationRecord) -> TraceStatusResponse:
        inv = rec.investigation
        return cls(
            trace_id=rec.trace_id,
            case_id=rec.case_id,
            start_address=rec.start_address,
            chain=rec.chain,
            status=rec.status,
            created_at=rec.created_at,
            started_at=rec.started_at,
            finished_at=rec.finished_at,
            block_heights=(
                {c.value: h for c, h in inv.block_heights.items()} if inv else {}
            ),
            result_hash=inv.result_hash() if inv else None,
            result=TraceResultOut.of(inv) if inv else None,
            error=rec.error,
        )


# --- graph ---------------------------------------------------------------


class GraphNodeOut(_Model):
    id: str
    chain: Chain
    kind: str
    risk: Decimal | None
    cluster_id: str | None
    vasp_name: str | None
    verified: bool | None
    typologies: list[str]

    @classmethod
    def of(cls, n: GraphNode) -> GraphNodeOut:
        return cls(
            id=n.address,
            chain=n.chain,
            kind=n.kind.value,
            risk=n.risk,
            cluster_id=n.cluster_id,
            vasp_name=n.vasp_name,
            verified=n.verified,
            typologies=list(n.typologies),
        )


class GraphEdgeOut(_Model):
    from_address: str = Field(serialization_alias="from")
    to_address: str = Field(serialization_alias="to")
    value: Decimal
    asset: str
    taint: Decimal
    tx_hash: str
    block_height: int
    timestamp: datetime

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @classmethod
    def of(cls, e: GraphEdge) -> GraphEdgeOut:
        return cls(
            from_address=e.from_address,
            to_address=e.to_address,
            value=e.value,
            asset=e.asset_symbol,
            taint=e.taint,
            tx_hash=e.tx_hash,
            block_height=e.block_height,
            timestamp=e.timestamp,
        )


class TraceGraphResponse(_Model):
    trace_id: str
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]

    @classmethod
    def of(cls, rec: InvestigationRecord) -> TraceGraphResponse:
        inv = rec.investigation
        nodes: list[GraphNodeOut] = []
        edges: list[GraphEdgeOut] = []
        if inv is not None and inv.result is not None:
            nodes = [GraphNodeOut.of(n) for n in inv.result.graph_nodes]
            edges = [GraphEdgeOut.of(e) for e in inv.result.graph_edges]
        return cls(trace_id=rec.trace_id, nodes=nodes, edges=edges)
