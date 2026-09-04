"""Two-tier attribution + the transparent confidence formula."""

import hashlib
import json
import shutil
from decimal import Decimal

from app.engine.attribution import (
    DEFAULT_WEIGHTS,
    EndpointContext,
    attribute,
)
from app.engine.labels import DEFAULT_LABEL_ROOT, LabelPack, LabelSet
from app.engine.records import Chain
from app.engine.result import AttributionTier
from app.engine.signals import SignalHit, SignalKind

PACK_ID = "aegis_demo_pack"
EXCH_HOT = "TVu3e6F8xVwuXiqyfgMyGenLMTKBy69YXH"


def endpoint(**overrides) -> EndpointContext:
    base: dict[str, object] = {
        "address": "Tendpoint",
        "chain": Chain.TRON,
        "hops_from_seed": 3,
        "taint_retained": Decimal("0.8"),
        "reaching_paths": 1,
        "mixer_on_path": False,
        "bridge_hops": 0,
        "deposit_address": "Tupstream",
        "is_sink": True,
        "vasp_signals": (),
        "cluster_addresses": (),
    }
    base.update(overrides)
    return EndpointContext(**base)  # type: ignore[arg-type]


def vasp_hit(name: str, score: str) -> SignalHit:
    return SignalHit(
        name=name, kind=SignalKind.VASP, score=Decimal(score),
        address="Tendpoint", evidence="e", limitations="l",
    )


def test_dataset_confirmed_when_address_is_labelled():
    labels = LabelSet.from_pack_ids([PACK_ID])
    cands = attribute([endpoint(address=EXCH_HOT, hops_from_seed=5,
                                taint_retained=Decimal("0.9336"))], labels)
    assert len(cands) == 1
    c = cands[0]
    assert c.tier is AttributionTier.DATASET_CONFIRMED
    assert c.name == "DemoExchange"
    assert c.source == PACK_ID
    assert c.confidence_terms is not None
    # score is the raw weighted sum, quantized, un-clamped (well within [0,1] here)
    assert abs(c.confidence_terms.raw_score - c.confidence_terms.score) < Decimal("0.001")
    assert Decimal("0.7") < c.confidence < Decimal("0.75")


def test_confidence_formula_matches_the_documented_weights():
    labels = LabelSet.from_pack_ids([PACK_ID])
    c = attribute(
        [endpoint(address=EXCH_HOT, hops_from_seed=5, taint_retained=Decimal("0.9336"),
                  reaching_paths=1, mixer_on_path=True)],
        labels,
    )[0]
    w = DEFAULT_WEIGHTS
    terms = c.confidence_terms
    assert terms is not None
    expected = (
        w.w1_source * terms.terms["source_score"]
        + w.w2_directness * terms.terms["path_directness"]
        + w.w3_taint * terms.terms["taint_retained"]
        + w.w4_corroboration * terms.terms["corroboration"]
        - w.p1_mixer * terms.terms["mixer_on_path"]
        - w.p2_bridge * terms.terms["bridge_uncertainty"]
    )
    assert abs(terms.raw_score - expected) < Decimal("0.0001")
    assert terms.terms["mixer_on_path"] == Decimal("1")


def test_heuristic_when_signals_but_no_label():
    cands = attribute([endpoint(vasp_signals=(vasp_hit("deposit_fan_in", "0.7"),))], None)
    c = cands[0]
    assert c.tier is AttributionTier.HEURISTIC
    assert c.name is None
    assert c.label == "Unidentified VASP-like endpoint"
    assert "deposit_fan_in" in c.signals
    assert c.confidence_terms is not None
    assert c.confidence_terms.terms["source_score"] <= Decimal("0.7")


def test_plain_sink_with_nothing_is_unknown_not_invented():
    c = attribute([endpoint()], None)[0]
    assert c.tier is AttributionTier.UNKNOWN
    assert c.name is None


def test_non_endpoint_intermediary_is_dropped():
    assert attribute([endpoint(is_sink=False, vasp_signals=())], None) == ()


def test_ranking_prefers_nearest_confirmed():
    labels = LabelSet.from_pack_ids([PACK_ID])
    far_confirmed = endpoint(address=EXCH_HOT, hops_from_seed=6)
    near_heuristic = endpoint(address="Theur", hops_from_seed=2,
                              vasp_signals=(vasp_hit("sweep_target", "0.6"),))
    ranked = attribute([near_heuristic, far_confirmed], labels)
    assert ranked[0].tier is AttributionTier.DATASET_CONFIRMED  # tier wins over distance
    assert [c.rank for c in ranked] == [1, 2]


def test_conflicting_labels_never_silently_pick_one(tmp_path):
    # a second pack that names EXCH_HOT differently
    other = tmp_path / "other_pack"
    shutil.copytree(DEFAULT_LABEL_ROOT / PACK_ID, other)
    rows = [
        r for r in json.loads((other / "labels.json").read_text())
        if r["label_type"] == "vasp"
    ]
    rows[0]["entity_name"] = "RivalExchange"
    text = json.dumps(rows, indent=2, sort_keys=True) + "\n"
    (other / "labels.json").write_text(text)
    manifest = json.loads((other / "manifest.json").read_text())
    manifest["pack_id"] = "other_pack"
    manifest["files"]["labels.json"]["sha256"] = hashlib.sha256(text.encode()).hexdigest()
    (other / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    labels = LabelSet(
        [LabelPack(PACK_ID), LabelPack("other_pack", root=tmp_path)]
    )
    c = attribute([endpoint(address=EXCH_HOT)], labels)[0]
    assert c.tier is AttributionTier.CONFLICT
    assert c.name is None
    assert "DemoExchange" in c.label and "RivalExchange" in c.label
