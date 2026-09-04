"""Tron address validation and constants."""

import pytest

from app.engine.errors import AddressFormatError
from app.engine.records import AssetKind, Chain
from app.engine.tron import (
    USDT_TRC20_CONTRACT,
    is_valid_tron_address,
    usdt_trc20,
    validate_tron_address,
)

# Real, well-known valid Tron addresses (contracts / burn address).
VALID = [
    USDT_TRC20_CONTRACT,
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",  # WIN token
]


@pytest.mark.parametrize("addr", VALID)
def test_accepts_valid_addresses(addr: str):
    assert is_valid_tron_address(addr)
    assert validate_tron_address(addr) == addr


@pytest.mark.parametrize(
    "addr",
    [
        "",
        "0x9a3c2f1b4d5e6f7890a1b2c3d4e5f60718293a4b",  # an EVM address
        "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj60",  # last char mangled -> bad checksum
        "XR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # wrong leading letter
        "TR7NH",  # too short
        "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t0OIl",  # invalid base58 chars
    ],
)
def test_rejects_bad_addresses(addr: str):
    assert not is_valid_tron_address(addr)
    with pytest.raises(AddressFormatError):
        validate_tron_address(addr)


def test_usdt_asset():
    asset = usdt_trc20()
    assert asset.chain is Chain.TRON
    assert asset.kind is AssetKind.TOKEN
    assert asset.decimals == 6
    assert asset.contract == USDT_TRC20_CONTRACT
