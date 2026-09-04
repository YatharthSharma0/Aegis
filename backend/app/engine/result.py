"""The trace-result boundary.

What the engine hands back and the backend (Phase 2) persists and serves. These
types map onto the ``GET /api/v1/trace/{id}`` and ``/graph`` response shapes in
the API contract, but carry no transport concerns (no ``trace_id``, no auth, no
pagination) — the backend adds those.

:class:`Investigation` is the top-level object. Its :meth:`Investigation.result_hash`
is the reproducibility anchor: it hashes the deterministic subset of the
investigation (excluding wall-clock timing), so the same cached input yields the
same hash on a clean checkout.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.engine.canonical import canonical_hash
from app.engine.errors import PartialReason, TrailLostReason
from app.engine.records import Address, Chain, HexHash, ProviderSnapshot

Unit = Annotated[Decimal, Field(ge=0, le=1)]
"""A dimensionless fraction in [0, 1] (risk, taint, confidence)."""

CONFIDENCE_WEIGHT_TOLERANCE = Decimal("0.0001")


class TraceStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"


class TaintModel(StrEnum):
    HAIRCUT = "haircut"
    POISON = "poison"


class NodeKind(StrEnum):
    SEED = "seed"
    INTERMEDIARY = "intermediary"
    CLUSTER_PEER = "cluster_peer"
    VASP_DEPOSIT = "vasp_deposit"
    MIXER = "mixer"
    BRIDGE = "bridge"
    SINK = "sink"


class AttributionTier(StrEnum):
    """Kept structurally distinct so a report never blurs these together."""

    DATASET_CONFIRMED = "dataset_confirmed"
    HEURISTIC = "heuristic"
    SANCTIONS = "sanctions"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TraceParams(_Model):
    """Bounds on the forward walk. All are explicit — no hidden defaults downstream."""

    max_hops: int = Field(default=8, ge=1, le=64)
    max_nodes: int = Field(default=5000, ge=1)
    max_edges: int = Field(default=20000, ge=1)
    min_value: Decimal = Field(default=Decimal("10"), ge=0)
    min_taint: Unit = Decimal("0.01")
    taint_model: TaintModel = TaintModel.HAIRCUT
    # Durations as Decimal seconds so params hash deterministically.
    per_provider_timeout_s: Decimal = Field(default=Decimal("10"), gt=0)
    total_deadline_s: Decimal = Field(default=Decimal("300"), gt=0)


class EvidenceRef(_Model):
    """Links one claim back to the recorded provider data it rests on."""

    provider: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    tx_hash: HexHash | None = None
    block_height: int | None = Field(default=None, ge=0)
    block_hash: HexHash | None = None
    captured_at: AwareDatetime | None = None


class GraphEdge(_Model):
    from_address: Address
    to_address: Address
    asset_symbol: str = Field(min_length=1)
    value: Decimal = Field(ge=0)
    value_raw: int = Field(ge=0)
    taint: Unit
    tx_hash: HexHash
    log_index: int | None = Field(default=None, ge=0)
    block_height: int = Field(ge=0)
    timestamp: AwareDatetime
    evidence: EvidenceRef


class GraphNode(_Model):
    address: Address
    chain: Chain
    kind: NodeKind
    risk: Unit | None = None
    cluster_id: str | None = None
    vasp_name: str | None = None
    verified: bool | None = None
    typologies: tuple[str, ...] = ()


class Cluster(_Model):
    cluster_id: str = Field(min_length=1)
    members: tuple[Address, ...] = Field(min_length=1)
    method: tuple[str, ...] = Field(min_length=1)
    confidence: Unit
    verified: bool = False
    rationale: str = ""


class ConfidenceTerms(_Model):
    """The transparent attribution score: per-term values, weights, and result.

    The full formula lands in Phase 1C. Here we guarantee the *shape*: weights
    cover exactly the terms, sum to 1, and ``score`` equals the weighted sum.
    """

    terms: dict[str, Decimal]
    weights: dict[str, Decimal]
    score: Unit

    @model_validator(mode="after")
    def _consistent(self) -> ConfidenceTerms:
        if set(self.terms) != set(self.weights):
            raise ValueError("terms and weights must cover the same keys")
        if not self.terms:
            raise ValueError("at least one term is required")
        weight_sum = sum(self.weights.values(), Decimal(0))
        if abs(weight_sum - Decimal(1)) > CONFIDENCE_WEIGHT_TOLERANCE:
            raise ValueError(f"weights must sum to 1 (got {weight_sum})")
        weighted = sum(
            (self.terms[k] * self.weights[k] for k in self.terms), Decimal(0)
        )
        if abs(weighted - self.score) > CONFIDENCE_WEIGHT_TOLERANCE:
            raise ValueError(
                f"score {self.score} != weighted sum of terms {weighted}"
            )
        return self


class VaspCandidate(_Model):
    rank: int = Field(ge=1)
    tier: AttributionTier
    source: str = Field(min_length=1)
    confidence: Unit
    name: str | None = None
    label: str | None = None
    confidence_terms: ConfidenceTerms | None = None
    deposit_address: Address | None = None
    reaching_paths: int = Field(default=1, ge=1)
    hops_from_seed: int = Field(ge=0)
    signals: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()

    @model_validator(mode="after")
    def _named_or_labelled(self) -> VaspCandidate:
        if self.name is None and not self.label:
            raise ValueError("candidate needs a name or a label")
        if self.tier is AttributionTier.DATASET_CONFIRMED and self.name is None:
            raise ValueError("dataset_confirmed candidate must have a name")
        return self


class TypologySignal(_Model):
    name: str = Field(min_length=1)
    score: Unit
    model: str = Field(pattern="^(rule|gnn)$")
    addresses: tuple[Address, ...] = ()


class TrailEvent(_Model):
    """A branch that legitimately stopped. Never a fabricated continuation."""

    reason: TrailLostReason
    address: Address | None = None
    asset_symbol: str | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    value_raw: int | None = Field(default=None, ge=0)
    timestamp: AwareDatetime | None = None
    evidence: EvidenceRef | None = None


class TraceResult(_Model):
    vasp_candidates: tuple[VaspCandidate, ...] = ()
    clusters: tuple[Cluster, ...] = ()
    typologies: tuple[TypologySignal, ...] = ()
    trail_events: tuple[TrailEvent, ...] = ()
    graph_nodes: tuple[GraphNode, ...] = ()
    graph_edges: tuple[GraphEdge, ...] = ()
    summary: str = ""

    @model_validator(mode="after")
    def _ranks_are_sequential(self) -> TraceResult:
        ranks = [c.rank for c in self.vasp_candidates]
        if ranks != sorted(ranks) or ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("vasp_candidates ranks must be 1..N in order")
        return self


class Investigation(_Model):
    """Top-level engine output for one seed address."""

    start_address: Address
    chain: Chain
    params: TraceParams
    status: TraceStatus
    partial_reason: PartialReason | None = None
    block_heights: dict[Chain, int] = Field(default_factory=dict)
    snapshots: tuple[ProviderSnapshot, ...] = ()
    result: TraceResult | None = None
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _status_consistency(self) -> Investigation:
        if self.status is TraceStatus.PARTIAL and self.partial_reason is None:
            raise ValueError("partial status requires a partial_reason")
        if self.status is not TraceStatus.PARTIAL and self.partial_reason is not None:
            raise ValueError("partial_reason is only valid with partial status")
        if self.status in (TraceStatus.DONE, TraceStatus.PARTIAL) and self.result is None:
            raise ValueError(f"{self.status} status requires a result")
        return self

    def __canonical__(self) -> dict[str, object]:
        # Deterministic subset only: wall-clock timing is excluded so repeated
        # runs over the same cached input hash identically.
        return {
            "start_address": self.start_address,
            "chain": self.chain,
            "params": self.params,
            "status": self.status,
            "partial_reason": self.partial_reason,
            "block_heights": {c.value: h for c, h in self.block_heights.items()},
            "snapshots": self.snapshots,
            "result": self.result,
        }

    def result_hash(self) -> str:
        """``"<schema>:<sha256>"`` over the deterministic subset of this object."""
        return canonical_hash(self)
