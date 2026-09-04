"""Standardized investigation report + SAHYOG notice draft.

Both are built deterministically from a finished :class:`InvestigationRecord` —
no new analysis, just a faithful rendering of what the engine produced, with the
provenance and the confidence arithmetic laid out for a court.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.domain.errors import InvalidRequestError, TraceNotReadyError
from app.domain.store import InvestigationRecord
from app.engine.result import Investigation, TraceStatus

_FINISHED = {TraceStatus.DONE, TraceStatus.PARTIAL}


def _require_finished(record: InvestigationRecord) -> Investigation:
    if record.status not in _FINISHED or record.investigation is None:
        raise TraceNotReadyError(record.trace_id, record.status.value)
    return record.investigation


def build_report(record: InvestigationRecord, *, generated_by: str | None) -> dict[str, Any]:
    inv = _require_finished(record)
    result = inv.result
    assert result is not None  # guaranteed by status check

    now = datetime.now(UTC)
    result_hash = inv.result_hash()

    candidates = [
        {
            "rank": c.rank,
            "tier": c.tier.value,
            "verified": c.tier.value == "dataset_confirmed",
            "name": c.name,
            "label": c.label,
            "source": c.source,
            "confidence": str(c.confidence),
            "confidence_formula": _formula(c),
            "deposit_address": c.deposit_address,
            "hops_from_seed": c.hops_from_seed,
            "reaching_paths": c.reaching_paths,
            "signals": list(c.signals),
            "evidence": [_evidence(e) for e in c.evidence],
        }
        for c in result.vasp_candidates
    ]

    fund_flow = [
        {
            "step": i + 1,
            "from": e.from_address,
            "to": e.to_address,
            "value": str(e.value),
            "asset": e.asset_symbol,
            "victim_taint": str(e.taint),
            "tx_hash": e.tx_hash,
            "block_height": e.block_height,
            "timestamp": e.timestamp.isoformat(),
            "provider": e.evidence.provider,
            "snapshot_id": e.evidence.snapshot_id,
        }
        for i, e in enumerate(result.graph_edges)
    ]

    return {
        "report_type": "aegis.investigation_report.v1",
        "header": {
            "trace_id": record.trace_id,
            "case_id": record.case_id,
            "reported_address": record.start_address,
            "chain": record.chain.value,
            "status": record.status.value,
            "partial_reason": inv.partial_reason.value if inv.partial_reason else None,
            "generated_at": now.isoformat(),
            "generated_by": generated_by,
            "block_heights": {c.value: h for c, h in inv.block_heights.items()},
            "result_hash": result_hash,
        },
        "officer_summary": result.summary,
        "vasp_candidates": candidates,
        "fund_flow": fund_flow,
        "typologies": [
            {"name": t.name, "score": str(t.score), "model": t.model,
             "addresses": list(t.addresses)}
            for t in result.typologies
        ],
        "trail_events": [
            {"reason": ev.reason.value, "address": ev.address,
             "asset": ev.asset_symbol, "amount": str(ev.amount) if ev.amount else None}
            for ev in result.trail_events
        ],
        "data_sources": [
            {
                "provider": s.provider,
                "endpoint": s.endpoint,
                "captured_at": s.captured_at.isoformat(),
                "response_checksum": s.response_checksum,
                "tip_block": {"height": s.tip_block.height, "hash": s.tip_block.block_hash},
                "record_count": s.record_count,
                "notes": s.notes,
            }
            for s in inv.snapshots
        ],
        "certification": {
            "statement": (
                "This report was generated deterministically from blockchain data "
                "recorded at the pinned block heights above. Re-running the trace "
                "against the same recorded data sources reproduces the result hash "
                f"{result_hash} exactly. Prepared as an electronic record for "
                "certification under section 63 of the Bharatiya Sakshya Adhiniyam, "
                "2023."
            ),
            "method": "value-weighted forward trace with haircut taint propagation",
            "reproducibility_anchor": result_hash,
            "generated_at": now.isoformat(),
        },
        "caveats": [
            "Attribution confidence is a transparent weighted score, not a verdict.",
            "Heuristic (unverified) endpoints require lawful inquiry to confirm the operator.",
            "This system is assistive; a human officer reviews before any action.",
        ],
    }


def _formula(candidate: Any) -> dict[str, Any] | None:
    terms = candidate.confidence_terms
    if terms is None:
        return None
    return {
        "terms": {k: str(v) for k, v in terms.terms.items()},
        "weights": {k: str(v) for k, v in terms.weights.items()},
        "raw_score": str(terms.raw_score),
        "score": str(terms.score),
    }


def _evidence(ref: Any) -> dict[str, Any]:
    return {
        "provider": ref.provider,
        "snapshot_id": ref.snapshot_id,
        "tx_hash": ref.tx_hash,
        "block_height": ref.block_height,
        "block_hash": ref.block_hash,
    }


def build_sahyog_notice(
    record: InvestigationRecord,
    *,
    vasp_rank: int,
    requesting_officer: str | None,
    case_ref: str | None,
    legal_basis: str | None,
) -> dict[str, Any]:
    inv = _require_finished(record)
    result = inv.result
    assert result is not None

    candidate = next(
        (c for c in result.vasp_candidates if c.rank == vasp_rank), None
    )
    if candidate is None:
        raise InvalidRequestError(
            f"no VASP candidate at rank {vasp_rank}",
            details={"available_ranks": [c.rank for c in result.vasp_candidates]},
        )

    vasp_name = candidate.name or candidate.label or "the receiving VASP"
    ref = case_ref or record.case_id or record.trace_id
    basis = legal_basis or "IT Act s.79(3)(b) read with BNSS provisions on preservation"
    asset_symbol = result.graph_edges[0].asset_symbol if result.graph_edges else ""
    traced_value = sum(
        (e.value for e in result.graph_edges if e.to_address == candidate.deposit_address),
        Decimal(0),
    )

    body = f"""\
To: {vasp_name} — Nodal / Compliance Officer

Subject: Request for preservation of records and account information — {ref}

1. This office is investigating cyber-financial fraud under reference {ref}.
   Funds reported by the victim from address {record.start_address} on the
   {record.chain.value} network have been traced on the public blockchain to a
   deposit address associated with your platform.

2. Deposit address: {candidate.deposit_address or "see technical annex"}
   Traced value reaching this address: {traced_value} {asset_symbol}
   Attribution: {candidate.tier.value} (confidence {candidate.confidence}); method and
   full arithmetic are in the attached investigation report (result hash
   {inv.result_hash()}).

3. You are requested, under {basis}, to:
   a. preserve all records, logs and KYC information relating to the account(s)
      linked to the above deposit address, and
   b. provide the account holder's identity and transaction history for the
      relevant period to the undersigned.

4. This is an assistive investigative lead; nothing herein directs a freeze.
   A formal order will follow as warranted.

Requesting officer: {requesting_officer or "____________________"}
Attachments: Aegis investigation report ({record.trace_id})
"""

    return {
        "notice_draft": {
            "to": f"{vasp_name} - Nodal/Compliance",
            "subject": f"Information/preservation request — {ref} — {vasp_name}",
            "body_markdown": body,
            "legal_basis": basis,
            "attachments": [f"aegis-report-{record.trace_id}.json"],
            "editable": True,
        },
        "based_on": {
            "trace_id": record.trace_id,
            "vasp_rank": vasp_rank,
            "result_hash": inv.result_hash(),
        },
    }
