"""Regenerate the synthetic ``growjoy_tron_trc20`` fixture.

Run from the backend directory:  ``python -m app.engine.fixtures.growjoy_tron_trc20._build``

This fixture is **synthetic** — hand-built, not recorded from a live chain. It
models a task-scam USDT-on-Tron cash-out so the engine's tracing, taint, fan-in
and trail-lost paths have deterministic input:

    seed ──1499.5──▶ rot1 ──1499.5──▶ rot2 ──1400──▶ cons ──▶ dep ──▶ exch_hot
                                        └────99.5────▶ mixer  (trail lost)
                       rot3 ────────────800──────────▶ cons

Addresses are real base58check-valid Tron addresses derived deterministically
from labels (see ``_addr``); they do **not** correspond to any real entity.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
HERE = Path(__file__).parent


def _b58encode(raw: bytes) -> str:
    num = int.from_bytes(raw, "big")
    out = ""
    while num > 0:
        num, rem = divmod(num, 58)
        out = _B58[rem] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + out


def _addr(label: str) -> str:
    payload = b"\x41" + hashlib.sha256(f"aegis-fixture-growjoy-{label}".encode()).digest()[:20]
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _b58encode(payload + checksum)


SEED = _addr("seed")
ROT1, ROT2, ROT3 = _addr("rot1"), _addr("rot2"), _addr("rot3")
CONS, DEP, EXCH_HOT, MIXER = _addr("cons"), _addr("dep"), _addr("exch_hot"), _addr("mixer")
USDT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # real USDT-TRC20 contract address

_TOKEN = {"symbol": "USDT", "address": USDT, "decimals": 6, "name": "Tether USD"}
_BASE_TS = 1_755_226_800_000  # 2026-08-15T03:00:00Z in ms


def _block_hash(block: int) -> str:
    return "0x" + hashlib.sha256(f"growjoy-block-{block}".encode()).hexdigest()


def _tx(idx: int, frm: str, to: str, usdt_amount: str, block: int) -> dict[str, object]:
    return {
        "transaction_id": "0x" + hashlib.sha256(f"growjoy-tx-{idx}".encode()).hexdigest(),
        "blockNumber": block,
        "blockHash": _block_hash(block),
        "block_timestamp": _BASE_TS + idx * 60_000,
        "from": frm,
        "to": to,
        "type": "Transfer",
        "value": str(int(Decimal(usdt_amount).scaleb(6))),
        "token_info": _TOKEN,
    }


TRANSFERS = [
    _tx(0, SEED, ROT1, "1499.5", 65_212_940),
    _tx(1, ROT1, ROT2, "1499.5", 65_212_950),
    _tx(2, ROT3, CONS, "800.0", 65_212_955),
    _tx(3, ROT2, CONS, "1400.0", 65_212_960),
    _tx(4, ROT2, MIXER, "99.5", 65_212_961),
    _tx(5, CONS, DEP, "2200.0", 65_212_980),
    _tx(6, DEP, EXCH_HOT, "2200.0", 65_213_000),
]

TIP_BLOCK = {
    "chain": "tron",
    "height": 65_213_001,
    "block_hash": "0x" + hashlib.sha256(b"growjoy-tip").hexdigest(),
    "timestamp": "2026-08-15T05:00:00.000000Z",
}


def _endpoints(record: dict[str, object]) -> tuple[str, str]:
    return str(record["from"]), str(record["to"])


def _activity() -> dict[str, dict[str, object]]:
    seen: dict[str, list[int]] = {}
    for transfer in TRANSFERS:
        ts = int(str(transfer["block_timestamp"]))
        for addr in _endpoints(transfer):
            seen.setdefault(addr, []).append(ts)
    out: dict[str, dict[str, object]] = {}
    for addr, times in seen.items():
        out[addr] = {
            "is_contract": False,
            "first_seen_ms": min(times),
            "last_seen_ms": max(times),
            "transfer_count": sum(1 for t in TRANSFERS if addr in _endpoints(t)),
        }
    # The token contract itself: party to every TRC-20 transfer in the set.
    all_ts = [int(str(t["block_timestamp"])) for t in TRANSFERS]
    out[USDT] = {
        "is_contract": True,
        "first_seen_ms": min(all_ts),
        "last_seen_ms": max(all_ts),
        "transfer_count": len(TRANSFERS),
    }
    return out


def _write(name: str, payload: object) -> str:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    (HERE / name).write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    transfers_sha = _write("transfers.json", TRANSFERS)
    activity_sha = _write("activity.json", _activity())
    manifest = {
        "fixture_id": "growjoy_tron_trc20",
        "synthetic": True,
        "description": (
            "SYNTHETIC — not real chain data. Hand-built task-scam USDT-on-Tron "
            "cash-out for engine tracing/taint/fan-in/trail-lost tests. Addresses "
            "are base58check-valid but correspond to no real entity."
        ),
        "chain": "tron",
        "provider": "fixture:trongrid",
        "endpoint": "/v1/accounts/{address}/transactions/trc20",
        "captured_at": "2026-08-20T00:00:00.000000Z",
        "schema_version": "aegis.engine.v1",
        "asset": {"symbol": "USDT", "contract": USDT, "decimals": 6},
        "seed_address": SEED,
        "tip_block": TIP_BLOCK,
        "files": {
            "transfers.json": {"sha256": transfers_sha},
            "activity.json": {"sha256": activity_sha},
        },
        "addresses": {
            "seed": SEED, "rot1": ROT1, "rot2": ROT2, "rot3": ROT3,
            "cons": CONS, "dep": DEP, "exch_hot": EXCH_HOT, "mixer": MIXER,
        },
    }
    _write("manifest.json", manifest)
    print("wrote manifest.json, transfers.json, activity.json")


if __name__ == "__main__":
    main()
