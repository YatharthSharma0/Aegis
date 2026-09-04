"""Aegis blockchain analytics engine.

A library (no HTTP, no DB, no I/O framework) that turns a victim-reported wallet
address into a fund-flow trace, wallet clusters, a VASP attribution lead, and
laundering-typology signals — with provenance from every claim back to a
recorded provider snapshot.

Phase 1A (this module set) defines only the *contract*:

- ``canonical`` — deterministic serialization + hashing rules (the reproducibility
  guarantee every later gate is checked against).
- ``errors`` — the engine error taxonomy and non-exception trail-outcome reasons.
- ``records`` — provenance-preserving internal records that provider adapters
  produce (``ProviderSnapshot``, ``NormalizedTransaction``, ``Transfer``,
  ``AddressActivity``).
- ``provider`` — the read-only ``ChainDataProvider`` interface adapters implement.
- ``result`` — the trace-result boundary the backend (Phase 2) consumes.

Nothing here fetches data or walks a graph; those arrive in Phase 1B onward.
"""

from app.engine.attribution import (
    ConfidenceWeights,
    EndpointContext,
    attribute,
)
from app.engine.canonical import (
    SCHEMA_VERSION,
    canonical_hash,
    canonical_json,
    sha256_hex,
)
from app.engine.errors import (
    AddressFormatError,
    ConfigurationError,
    EngineError,
    FixtureError,
    PartialReason,
    ProviderError,
    ProviderRateLimitedError,
    ProviderResponseInvalidError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    TrailLostReason,
    UnsupportedAssetError,
    UnsupportedChainError,
)
from app.engine.labels import (
    Label,
    LabelPack,
    LabelSet,
    LabelType,
)
from app.engine.provider import (
    ActivityResult,
    BlockResult,
    ChainDataProvider,
    ProviderCapabilities,
    TransferPage,
)
from app.engine.providers import FixtureProvider
from app.engine.records import (
    AddressActivity,
    Asset,
    AssetKind,
    BlockRef,
    Chain,
    NormalizedTransaction,
    ProviderSnapshot,
    Transfer,
    TxStatus,
)
from app.engine.result import (
    AttributionTier,
    Cluster,
    ConfidenceTerms,
    EvidenceRef,
    GraphEdge,
    GraphNode,
    Investigation,
    NodeKind,
    TaintModel,
    TraceParams,
    TraceResult,
    TraceStatus,
    TrailEvent,
    TypologySignal,
    VaspCandidate,
)
from app.engine.signals import (
    AddressStats,
    SignalConfig,
    SignalHit,
    SignalKind,
    SignalReport,
    detect_account_signals,
)
from app.engine.tron import (
    USDT_TRC20_CONTRACT,
    is_valid_tron_address,
    usdt_trc20,
    validate_tron_address,
)
from app.engine.walk import forward_trace

__all__ = [
    "SCHEMA_VERSION",
    "USDT_TRC20_CONTRACT",
    "ActivityResult",
    "AddressActivity",
    "AddressFormatError",
    "AddressStats",
    "Asset",
    "AssetKind",
    "AttributionTier",
    "BlockRef",
    "BlockResult",
    "Chain",
    "ChainDataProvider",
    "Cluster",
    "ConfidenceTerms",
    "ConfidenceWeights",
    "ConfigurationError",
    "EndpointContext",
    "EngineError",
    "EvidenceRef",
    "FixtureError",
    "FixtureProvider",
    "GraphEdge",
    "GraphNode",
    "Investigation",
    "Label",
    "LabelPack",
    "LabelSet",
    "LabelType",
    "NodeKind",
    "NormalizedTransaction",
    "PartialReason",
    "ProviderCapabilities",
    "ProviderError",
    "ProviderRateLimitedError",
    "ProviderResponseInvalidError",
    "ProviderSnapshot",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "SignalConfig",
    "SignalHit",
    "SignalKind",
    "SignalReport",
    "TaintModel",
    "TraceParams",
    "TraceResult",
    "TraceStatus",
    "TrailEvent",
    "TrailLostReason",
    "Transfer",
    "TransferPage",
    "TxStatus",
    "TypologySignal",
    "UnsupportedAssetError",
    "UnsupportedChainError",
    "VaspCandidate",
    "attribute",
    "canonical_hash",
    "canonical_json",
    "detect_account_signals",
    "forward_trace",
    "is_valid_tron_address",
    "sha256_hex",
    "usdt_trc20",
    "validate_tron_address",
]
