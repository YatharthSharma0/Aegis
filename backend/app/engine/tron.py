"""Tron-specific constants and address validation.

Kept dependency-free: base58check is small and vendoring it avoids pulling a
crypto library into the engine for one function.
"""

from __future__ import annotations

import hashlib

from app.engine.errors import AddressFormatError
from app.engine.records import Asset, AssetKind, Chain

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {ch: i for i, ch in enumerate(_B58_ALPHABET)}

#: Mainnet address payload prefix byte (0x41) — every base58 Tron address is `T…`.
TRON_ADDRESS_PREFIX = 0x41
_ADDRESS_PAYLOAD_LEN = 21  # prefix byte + 20-byte account
_CHECKSUM_LEN = 4

#: Tether USD on Tron (TRC-20), 6 decimals. The asset Aegis traces by default.
USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_TRC20_DECIMALS = 6


def _b58decode(text: str) -> bytes:
    num = 0
    for char in text:
        try:
            num = num * 58 + _B58_INDEX[char]
        except KeyError:
            raise AddressFormatError(f"invalid base58 character {char!r}") from None
    body = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    pad = len(text) - len(text.lstrip("1"))
    return b"\x00" * pad + body


def is_valid_tron_address(address: str) -> bool:
    """Return whether ``address`` is a well-formed base58check Tron address."""
    try:
        validate_tron_address(address)
    except AddressFormatError:
        return False
    return True


def validate_tron_address(address: str) -> str:
    """Return ``address`` unchanged if valid, else raise :class:`AddressFormatError`."""
    if not address or address[0] != "T":
        raise AddressFormatError(f"Tron address must start with 'T': {address!r}")
    raw = _b58decode(address)
    if len(raw) != _ADDRESS_PAYLOAD_LEN + _CHECKSUM_LEN:
        raise AddressFormatError(f"Tron address has wrong length: {address!r}")
    payload, checksum = raw[:_ADDRESS_PAYLOAD_LEN], raw[_ADDRESS_PAYLOAD_LEN:]
    if payload[0] != TRON_ADDRESS_PREFIX:
        raise AddressFormatError(f"Tron address has wrong prefix byte: {address!r}")
    digest = hashlib.sha256(hashlib.sha256(payload).digest()).digest()
    if digest[:_CHECKSUM_LEN] != checksum:
        raise AddressFormatError(f"Tron address checksum mismatch: {address!r}")
    return address


def usdt_trc20() -> Asset:
    """The USDT-on-Tron asset record."""
    return Asset(
        chain=Chain.TRON,
        kind=AssetKind.TOKEN,
        symbol="USDT",
        decimals=USDT_TRC20_DECIMALS,
        contract=USDT_TRC20_CONTRACT,
    )
