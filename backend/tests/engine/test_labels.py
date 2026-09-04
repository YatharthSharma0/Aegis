"""Label packs: loading, checksum integrity, VASP-vs-sanctions separation."""

import json
import shutil
from pathlib import Path

import pytest

from app.engine.errors import FixtureError
from app.engine.labels import DEFAULT_LABEL_ROOT, LabelPack, LabelSet, LabelType
from app.engine.records import Chain

PACK_ID = "aegis_demo_pack"
EXCH_HOT = "TVu3e6F8xVwuXiqyfgMyGenLMTKBy69YXH"
MIXER = "TBhz6rKUfXj9nqXbRmcrzpJ4stfYaVr4YW"


def test_demo_pack_loads_with_provenance():
    pack = LabelPack(PACK_ID)
    assert pack.meta.synthetic is True
    assert pack.meta.licence
    assert pack.meta.last_verified.year == 2026
    assert {label.entity_name for label in pack.labels} == {"DemoExchange", "DemoMixer"}
    for label in pack.labels:
        assert label.pack_id == PACK_ID
        assert label.source == pack.meta.source


def test_missing_pack_raises():
    with pytest.raises(FixtureError):
        LabelPack("no_such_pack")


def test_checksum_mismatch_raises(tmp_path: Path):
    dst = tmp_path / PACK_ID
    shutil.copytree(DEFAULT_LABEL_ROOT / PACK_ID, dst)
    rows = json.loads((dst / "labels.json").read_text())
    rows[0]["entity_name"] = "TamperedExchange"
    (dst / "labels.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    with pytest.raises(FixtureError, match="checksum mismatch"):
        LabelPack(PACK_ID, root=tmp_path)


def test_lookup_filters_by_type():
    labels = LabelSet.from_pack_ids([PACK_ID])
    vasp = labels.lookup(EXCH_HOT, Chain.TRON, types=[LabelType.VASP])
    assert len(vasp) == 1
    assert vasp[0].entity_name == "DemoExchange"
    # the mixer address is not a VASP
    assert labels.lookup(MIXER, Chain.TRON, types=[LabelType.VASP]) == ()
    assert labels.lookup(MIXER, Chain.TRON, types=[LabelType.MIXER])[0].entity_name == "DemoMixer"


def test_addresses_of_type():
    labels = LabelSet.from_pack_ids([PACK_ID])
    assert labels.addresses_of_type(LabelType.MIXER, Chain.TRON) == frozenset({MIXER})
    assert labels.addresses_of_type(LabelType.VASP, Chain.TRON) == frozenset({EXCH_HOT})
    assert labels.addresses_of_type(LabelType.BRIDGE, Chain.TRON) == frozenset()


def test_wrong_chain_does_not_match():
    labels = LabelSet.from_pack_ids([PACK_ID])
    assert labels.lookup(EXCH_HOT, Chain.ETHEREUM) == ()
