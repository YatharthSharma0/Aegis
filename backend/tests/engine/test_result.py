"""Trace-result boundary: consistency rules and the reproducibility anchor."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine.errors import PartialReason
from app.engine.records import Chain
from app.engine.result import (
    AttributionTier,
    ConfidenceTerms,
    Investigation,
    TraceParams,
    TraceResult,
    TraceStatus,
    VaspCandidate,
)
from tests.engine.conftest import SEED


def make_terms(score: str = "0.5") -> ConfidenceTerms:
    return ConfidenceTerms(
        terms={"source": Decimal("1.0"), "directness": Decimal("0.0")},
        weights={"source": Decimal("0.5"), "directness": Decimal("0.5")},
        score=Decimal(score),
    )


# --- ConfidenceTerms -------------------------------------------------------


def test_confidence_terms_weights_need_not_sum_to_one():
    # penalty terms have negative weights; the sum is not 1
    terms = ConfidenceTerms(
        terms={"source": Decimal("1"), "mixer_penalty": Decimal("1")},
        weights={"source": Decimal("0.45"), "mixer_penalty": Decimal("-0.25")},
        score=Decimal("0.20"),
    )
    assert terms.raw_score == Decimal("0.20")


def test_confidence_terms_score_must_equal_clamped_weighted_sum():
    with pytest.raises(ValidationError):
        ConfidenceTerms(
            terms={"a": Decimal("1"), "b": Decimal("0")},
            weights={"a": Decimal("0.5"), "b": Decimal("0.5")},
            score=Decimal("0.9"),
        )


def test_confidence_terms_score_is_clamped_to_unit_range():
    # raw weighted sum is 1.4 -> score clamps to 1
    terms = ConfidenceTerms(
        terms={"a": Decimal("1"), "b": Decimal("1")},
        weights={"a": Decimal("0.9"), "b": Decimal("0.5")},
        score=Decimal("1"),
    )
    assert terms.raw_score == Decimal("1.4")


def test_confidence_terms_keys_must_match():
    with pytest.raises(ValidationError):
        ConfidenceTerms(
            terms={"a": Decimal("1")},
            weights={"b": Decimal("1")},
            score=Decimal("1"),
        )


def test_confidence_terms_accepts_a_consistent_breakdown():
    terms = make_terms("0.5")
    assert terms.score == Decimal("0.5")


# --- VaspCandidate -------------------------------------------------------


def test_candidate_requires_name_or_label():
    with pytest.raises(ValidationError):
        VaspCandidate(rank=1, tier=AttributionTier.HEURISTIC, source="heuristic",
                      confidence=Decimal("0.4"), hops_from_seed=2)


def test_dataset_confirmed_candidate_requires_a_name():
    with pytest.raises(ValidationError):
        VaspCandidate(rank=1, tier=AttributionTier.DATASET_CONFIRMED, source="tagpack",
                      confidence=Decimal("0.9"), label="only a label", hops_from_seed=1)


def test_heuristic_candidate_may_be_label_only():
    cand = VaspCandidate(
        rank=1, tier=AttributionTier.HEURISTIC, source="heuristic",
        confidence=Decimal("0.54"), label="Unidentified VASP-like endpoint",
        hops_from_seed=3, signals=("deposit-fan-in",),
    )
    assert cand.name is None


# --- TraceResult -------------------------------------------------------


def test_vasp_candidate_ranks_must_be_sequential():
    c1 = VaspCandidate(rank=1, tier=AttributionTier.HEURISTIC, source="h",
                       confidence=Decimal("0.5"), label="x", hops_from_seed=1)
    c3 = VaspCandidate(rank=3, tier=AttributionTier.HEURISTIC, source="h",
                       confidence=Decimal("0.4"), label="y", hops_from_seed=2)
    with pytest.raises(ValidationError):
        TraceResult(vasp_candidates=(c1, c3))


def test_empty_result_is_valid():
    assert TraceResult().vasp_candidates == ()


# --- Investigation -------------------------------------------------------


def _done_investigation(**overrides) -> Investigation:
    base = {
        "start_address": SEED,
        "chain": Chain.TRON,
        "params": TraceParams(),
        "status": TraceStatus.DONE,
        "result": TraceResult(summary="landed at a heuristic endpoint"),
        "block_heights": {Chain.TRON: 65_213_001},
    }
    base.update(overrides)
    return Investigation(**base)


def test_done_status_requires_a_result():
    with pytest.raises(ValidationError):
        Investigation(start_address=SEED, chain=Chain.TRON, params=TraceParams(),
                      status=TraceStatus.DONE)


def test_partial_status_requires_a_reason():
    with pytest.raises(ValidationError):
        Investigation(start_address=SEED, chain=Chain.TRON, params=TraceParams(),
                      status=TraceStatus.PARTIAL, result=TraceResult())


def test_partial_reason_only_valid_with_partial_status():
    with pytest.raises(ValidationError):
        _done_investigation(partial_reason=PartialReason.DEADLINE)


def test_partial_investigation_is_accepted():
    inv = Investigation(
        start_address=SEED, chain=Chain.TRON, params=TraceParams(),
        status=TraceStatus.PARTIAL, partial_reason=PartialReason.DEADLINE,
        result=TraceResult(),
    )
    assert inv.partial_reason is PartialReason.DEADLINE


def test_result_hash_is_schema_prefixed():
    digest = _done_investigation().result_hash()
    assert digest.startswith("aegis.engine.v1:")
    assert len(digest.split(":", 1)[1]) == 64


def test_result_hash_ignores_wall_clock_timing():
    early = _done_investigation(
        started_at=datetime(2026, 8, 14, 19, 0, tzinfo=UTC),
        finished_at=datetime(2026, 8, 14, 19, 3, tzinfo=UTC),
    )
    late = _done_investigation(
        started_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        finished_at=datetime(2026, 9, 1, 8, 9, tzinfo=UTC),
    )
    assert early.result_hash() == late.result_hash()


def test_result_hash_changes_when_the_result_changes():
    a = _done_investigation(result=TraceResult(summary="one"))
    b = _done_investigation(result=TraceResult(summary="two"))
    assert a.result_hash() != b.result_hash()


def test_result_hash_changes_with_params():
    a = _done_investigation(params=TraceParams(max_hops=8))
    b = _done_investigation(params=TraceParams(max_hops=6))
    assert a.result_hash() != b.result_hash()
