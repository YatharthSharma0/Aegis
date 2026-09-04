"""Account-model structural signal detectors."""

from datetime import UTC, datetime
from decimal import Decimal

from app.engine.signals import (
    AddressStats,
    SignalConfig,
    SignalKind,
    detect_account_signals,
)

TS = datetime(2026, 8, 15, 3, 0, tzinfo=UTC)


def stats(**overrides) -> AddressStats:
    base: dict[str, object] = {
        "address": "Tx",
        "is_seed": False,
        "is_contract": False,
        "total_in": Decimal("100"),
        "total_out": Decimal("100"),
        "distinct_senders": 1,
        "distinct_recipients": 1,
        "incoming_count": 1,
        "outgoing_count": 1,
        "largest_out_fraction": Decimal("1"),
        "first_activity": TS,
        "last_activity": TS,
        "forward_latency_s": Decimal("60"),
    }
    base.update(overrides)
    return AddressStats(**base)  # type: ignore[arg-type]


def names(report) -> set[str]:
    return {h.name for h in report.hits}


def test_passthrough_rotation_fires_on_a_prompt_full_forward():
    report = detect_account_signals([stats()])
    assert "passthrough_rotation" in names(report)
    hit = next(h for h in report.hits if h.name == "passthrough_rotation")
    assert hit.kind is SignalKind.TYPOLOGY
    assert hit.evidence and hit.limitations


def test_seed_is_never_flagged():
    assert detect_account_signals([stats(is_seed=True)]).hits == ()


def test_partial_forward_does_not_look_like_rotation():
    assert "passthrough_rotation" not in names(
        detect_account_signals([stats(total_out=Decimal("40"))])
    )


def test_peel_chain_needs_a_dominant_output_plus_a_peel():
    report = detect_account_signals(
        [stats(outgoing_count=3, distinct_recipients=3, largest_out_fraction=Decimal("0.95"))]
    )
    assert "peel_chain" in names(report)


def test_deposit_fan_in_is_a_vasp_signal_not_a_typology():
    report = detect_account_signals(
        [
            stats(
                distinct_senders=25,
                distinct_recipients=1,
                incoming_count=25,
                largest_out_fraction=Decimal("0.99"),
                forward_latency_s=Decimal("120"),
            )
        ]
    )
    assert "deposit_fan_in" in names(report)
    hit = next(h for h in report.hits if h.name == "deposit_fan_in")
    assert hit.kind is SignalKind.VASP
    assert report.typologies() == () or all(
        t.name != "deposit_fan_in" for t in report.typologies()
    )


def test_deposit_fan_in_needs_fast_forwarding():
    report = detect_account_signals(
        [
            stats(
                distinct_senders=25, distinct_recipients=1, incoming_count=25,
                largest_out_fraction=Decimal("0.99"), forward_latency_s=Decimal("100000"),
            )
        ]
    )
    assert "deposit_fan_in" not in names(report)


def test_sweep_target_on_high_in_degree():
    report = detect_account_signals(
        [stats(incoming_count=40, distinct_senders=30, distinct_recipients=2,
               total_out=Decimal("100"), largest_out_fraction=Decimal("0.6"))]
    )
    assert "sweep_target" in names(report)


def test_batch_withdrawals_on_wide_fan_out():
    report = detect_account_signals(
        [stats(distinct_recipients=40, outgoing_count=40, largest_out_fraction=Decimal("0.1"))]
    )
    assert "batch_withdrawals" in names(report)
    assert "rapid_fan_out" in names(report)  # both lenses fire


def test_thresholds_are_configurable():
    tiny = SignalConfig(fan_in_min_senders=2, sweep_min_incoming=2)
    report = detect_account_signals(
        [stats(distinct_senders=2, incoming_count=3, distinct_recipients=2,
               largest_out_fraction=Decimal("0.6"))],
        config=tiny,
    )
    assert "sweep_target" in names(report)


def test_labels_and_typologies_helpers():
    report = detect_account_signals([stats(address="Ta"), stats(address="Tb", is_seed=True)])
    assert report.labels_for("Ta") == ("passthrough_rotation",)
    assert report.labels_for("Tb") == ()
    typ = report.typologies()
    assert len(typ) == 1
    assert typ[0].model == "rule"
