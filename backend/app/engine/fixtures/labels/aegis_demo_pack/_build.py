"""Regenerate the synthetic ``aegis_demo_pack`` label pack.

    python -m app.engine.fixtures.labels.aegis_demo_pack._build

**Synthetic** — the entities and addresses are fictional, matched to the
``growjoy_tron_trc20`` fixture so an end-to-end trace lands on a
dataset-confirmed VASP and a labelled mixer. Not for real attribution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent

# Addresses from app/engine/fixtures/growjoy_tron_trc20/manifest.json
EXCH_HOT = "TVu3e6F8xVwuXiqyfgMyGenLMTKBy69YXH"
MIXER = "TBhz6rKUfXj9nqXbRmcrzpJ4stfYaVr4YW"

LABELS = [
    {
        "address": EXCH_HOT,
        "chain": "tron",
        "label_type": "vasp",
        "entity_name": "DemoExchange",
        "category": "exchange_hot_wallet",
        "confidence": "0.95",
    },
    {
        "address": MIXER,
        "chain": "tron",
        "label_type": "mixer",
        "entity_name": "DemoMixer",
        "category": "mixer",
        "confidence": "0.9",
    },
]


def _write(name: str, payload: object) -> str:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    (HERE / name).write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    labels_sha = _write("labels.json", LABELS)
    manifest = {
        "pack_id": "aegis_demo_pack",
        "synthetic": True,
        "description": (
            "SYNTHETIC demo label pack matched to the growjoy_tron_trc20 fixture: "
            "one confirmed VASP hot wallet and one labelled mixer. Fictional."
        ),
        "source": "aegis-internal-synthetic",
        "licence": "MIT (this repo)",
        "last_verified": "2026-08-20",
        "files": {"labels.json": {"sha256": labels_sha}},
    }
    _write("manifest.json", manifest)
    print("wrote manifest.json, labels.json")


if __name__ == "__main__":
    main()
