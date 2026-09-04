"""Canonical serialization + hashing rules."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

import pytest

from app.engine.canonical import (
    SCHEMA_VERSION,
    canonical_hash,
    canonical_json,
    sha256_hex,
)

IST = timezone(timedelta(hours=5, minutes=30))


class Colour(Enum):
    RED = "red"
    ONE = 1


def test_object_keys_are_sorted_and_whitespace_stripped():
    assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_insertion_order_does_not_change_output():
    a = canonical_json({"x": 1, "y": {"p": 2, "q": 3}})
    b = canonical_json({"y": {"q": 3, "p": 2}, "x": 1})
    assert a == b


def test_float_is_rejected():
    with pytest.raises(TypeError):
        canonical_json({"v": 1.5})


def test_set_is_rejected():
    with pytest.raises(TypeError):
        canonical_json({"v": {1, 2, 3}})


def test_non_string_key_is_rejected():
    with pytest.raises(TypeError):
        canonical_json({1: "a"})


def test_decimal_is_fixed_point_string():
    assert canonical_json({"v": Decimal("1.50")}) == b'{"v":"1.50"}'
    assert canonical_json({"v": Decimal("1E-6")}) == b'{"v":"0.000001"}'


def test_decimal_scale_is_significant():
    assert canonical_json(Decimal("1.5")) != canonical_json(Decimal("1.50"))


def test_datetime_normalized_to_utc_with_six_fractional_digits():
    dt = datetime(2026, 8, 14, 19, 0, 0, tzinfo=UTC)
    assert canonical_json(dt) == b'"2026-08-14T19:00:00.000000Z"'


def test_datetime_offset_is_converted_to_utc():
    # 2026-08-15 06:00 IST == 2026-08-15 00:30 UTC
    ist_dt = datetime(2026, 8, 15, 6, 0, 0, tzinfo=IST)
    assert canonical_json(ist_dt) == b'"2026-08-15T00:30:00.000000Z"'


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        canonical_json(datetime(2026, 1, 1, 0, 0, 0))


def test_bytes_are_lowercase_hex():
    assert canonical_json(b"\x00\xab\xff") == b'"00abff"'


def test_enum_is_replaced_by_value():
    assert canonical_json(Colour.RED) == b'"red"'
    assert canonical_json(Colour.ONE) == b"1"


def test_canonicalizable_protocol_is_honoured():
    class Wrapped:
        def __canonical__(self) -> object:
            return {"only": "this"}

    assert canonical_json(Wrapped()) == b'{"only":"this"}'


def test_unknown_type_is_rejected():
    with pytest.raises(TypeError):
        canonical_json(object())


def test_hash_is_schema_prefixed_sha256():
    digest = canonical_hash({"a": 1})
    prefix, _, hexpart = digest.partition(":")
    assert prefix == SCHEMA_VERSION
    assert len(hexpart) == 64
    assert hexpart == sha256_hex(canonical_json({"a": 1}))


def test_hash_changes_when_data_changes():
    assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})
