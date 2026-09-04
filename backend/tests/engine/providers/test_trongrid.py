"""TronGridProvider — parsing, pagination, retry/backoff, caching, key
hygiene — entirely offline via ``httpx.MockTransport``. No test here makes a
real network call; CI stays fully offline (Phase 4.5 acceptance criterion).
"""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.engine.errors import (
    ConfigurationError,
    ProviderRateLimitedError,
    ProviderResponseInvalidError,
    ProviderUnavailableError,
    UnsupportedChainError,
)
from app.engine.providers import FixtureProvider, TronGridProvider, get_provider
from app.engine.records import Chain
from app.engine.tron import USDT_TRC20_CONTRACT, usdt_trc20

API_KEY = "test-key-should-never-leak-0123456789abcdef"
ADDR = "TXYZaddr0000000000000000000000000000"
CONTRACT = USDT_TRC20_CONTRACT
TX = "abc123"
BLOCK_NUM = 42
BLOCK_ID = "0" * 63 + "1"


def _nowblock_body() -> dict:
    return {
        "blockID": "f" * 64,
        "block_header": {"raw_data": {"number": 999, "timestamp": 1_700_000_000_000}},
    }


def _trc20_page_body(*, fingerprint: str | None = None) -> dict:
    return {
        "data": [
            {
                "transaction_id": TX,
                "token_info": {"address": CONTRACT, "decimals": 6, "symbol": "USDT"},
                "block_timestamp": 1_700_000_001_000,
                "from": ADDR,
                "to": "TReceiver00000000000000000000000000",
                "value": "1500000",
            }
        ],
        "success": True,
        "meta": {"fingerprint": fingerprint} if fingerprint else {},
    }


def _tx_info_body() -> dict:
    return {"id": TX, "blockNumber": BLOCK_NUM, "blockTimeStamp": 1_700_000_001_000}


def _block_body() -> dict:
    return {"blockID": BLOCK_ID, "block_header": {"raw_data": {"number": BLOCK_NUM}}}


def _account_body() -> dict:
    return {"data": [{"address": ADDR, "create_time": 1_600_000_000_000}], "success": True}


def _handler(routes: dict[str, httpx.Response | Exception]):
    calls: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        key = request.url.path.lstrip("/")
        calls.append(key)
        assert request.headers.get("TRON-PRO-API-KEY") == API_KEY
        outcome = routes[key]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    handle.calls = calls  # type: ignore[attr-defined]
    return handle


def _provider(routes: dict[str, httpx.Response | Exception], **kwargs) -> TronGridProvider:
    transport = httpx.MockTransport(_handler(routes))
    return TronGridProvider(api_key=API_KEY, transport=transport, sleep=lambda _s: None, **kwargs)


def test_latest_block_parses_tip_from_getnowblock():
    provider = _provider({"wallet/getnowblock": httpx.Response(200, json=_nowblock_body())})
    result = provider.latest_block()
    assert result.block.height == 999
    assert result.block.block_hash == "f" * 64
    assert result.snapshot.provider == "trongrid"
    # The key must never leak into recorded provenance.
    assert API_KEY not in str(result.snapshot.request_params)


def test_token_transfers_enriches_block_height_and_hash():
    provider = _provider(
        {
            "wallet/getnowblock": httpx.Response(200, json=_nowblock_body()),
            f"v1/accounts/{ADDR}/transactions/trc20": httpx.Response(
                200, json=_trc20_page_body()
            ),
            "wallet/gettransactioninfobyid": httpx.Response(200, json=_tx_info_body()),
            "wallet/getblockbynum": httpx.Response(200, json=_block_body()),
        }
    )
    page = provider.token_transfers(ADDR, asset=usdt_trc20())
    assert len(page.transactions) == 1
    tx = page.transactions[0]
    transfer = tx.transfers[0]
    assert transfer.block_height == BLOCK_NUM
    assert transfer.block_hash == BLOCK_ID
    assert transfer.value == Decimal("1.500000")
    assert transfer.value_raw == 1_500_000
    assert page.next_cursor is None  # no fingerprint in this fixture's meta


def test_token_transfers_pagination_cursor_is_the_fingerprint():
    provider = _provider(
        {
            "wallet/getnowblock": httpx.Response(200, json=_nowblock_body()),
            f"v1/accounts/{ADDR}/transactions/trc20": httpx.Response(
                200, json=_trc20_page_body(fingerprint="next-page-token")
            ),
            "wallet/gettransactioninfobyid": httpx.Response(200, json=_tx_info_body()),
            "wallet/getblockbynum": httpx.Response(200, json=_block_body()),
        }
    )
    page = provider.token_transfers(ADDR, asset=usdt_trc20())
    assert page.next_cursor == "next-page-token"


def test_tx_info_and_block_hash_are_cached_across_transfers_in_the_same_tx():
    """One tx with two logged transfers must only call the enrichment
    endpoints once each — proves the tx_hash/block_number caching."""
    body = _trc20_page_body()
    body["data"].append({**body["data"][0]})  # same tx_hash, second transfer
    handler = _handler(
        {
            "wallet/getnowblock": httpx.Response(200, json=_nowblock_body()),
            f"v1/accounts/{ADDR}/transactions/trc20": httpx.Response(200, json=body),
            "wallet/gettransactioninfobyid": httpx.Response(200, json=_tx_info_body()),
            "wallet/getblockbynum": httpx.Response(200, json=_block_body()),
        }
    )
    provider = TronGridProvider(
        api_key=API_KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None
    )
    provider.token_transfers(ADDR, asset=usdt_trc20())
    assert handler.calls.count("wallet/gettransactioninfobyid") == 1
    assert handler.calls.count("wallet/getblockbynum") == 1


def test_address_activity_reports_is_contract_from_getcontract():
    provider = _provider(
        {
            "wallet/getnowblock": httpx.Response(200, json=_nowblock_body()),
            f"v1/accounts/{ADDR}": httpx.Response(200, json=_account_body()),
            "wallet/getcontract": httpx.Response(200, json={"bytecode": "6080"}),
        }
    )
    result = provider.address_activity(ADDR)
    assert result.activity.is_contract is True
    assert result.activity.transfer_count == 0  # documented limitation


def test_address_activity_not_a_contract_when_getcontract_is_empty():
    provider = _provider(
        {
            "wallet/getnowblock": httpx.Response(200, json=_nowblock_body()),
            f"v1/accounts/{ADDR}": httpx.Response(200, json=_account_body()),
            "wallet/getcontract": httpx.Response(200, json={}),
        }
    )
    result = provider.address_activity(ADDR)
    assert result.activity.is_contract is False


def test_429_is_retried_then_raises_rate_limited_at_the_end():
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "1"}, json={})

    provider = TronGridProvider(
        api_key=API_KEY, transport=httpx.MockTransport(handle), sleep=lambda _s: None
    )
    with pytest.raises(ProviderRateLimitedError):
        provider.latest_block()
    assert calls["n"] >= 2  # at least one retry happened


def test_5xx_is_retried_then_succeeds():
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json=_nowblock_body())

    provider = TronGridProvider(
        api_key=API_KEY, transport=httpx.MockTransport(handle), sleep=lambda _s: None
    )
    result = provider.latest_block()
    assert result.block.height == 999
    assert calls["n"] == 2


def test_transport_error_is_retried_then_raises_unavailable():
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = TronGridProvider(
        api_key=API_KEY, transport=httpx.MockTransport(handle), sleep=lambda _s: None
    )
    with pytest.raises(ProviderUnavailableError):
        provider.latest_block()


def test_a_400_is_not_retried():
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, text="bad request")

    provider = TronGridProvider(
        api_key=API_KEY, transport=httpx.MockTransport(handle), sleep=lambda _s: None
    )
    with pytest.raises(ProviderResponseInvalidError):
        provider.latest_block()
    assert calls["n"] == 1


def test_response_cache_avoids_a_second_network_call(tmp_path):
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=_nowblock_body())

    provider = TronGridProvider(
        api_key=API_KEY,
        transport=httpx.MockTransport(handle),
        sleep=lambda _s: None,
        cache_dir=tmp_path,
    )
    provider.latest_block()
    provider.latest_block()
    assert calls["n"] == 1


def test_no_cache_dir_hits_the_network_every_time():
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=_nowblock_body())

    provider = TronGridProvider(
        api_key=API_KEY, transport=httpx.MockTransport(handle), sleep=lambda _s: None
    )
    provider.latest_block()
    provider.latest_block()
    assert calls["n"] == 2


def test_api_key_never_appears_in_a_raised_error_message():
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request, nothing sensitive here")

    provider = TronGridProvider(
        api_key=API_KEY, transport=httpx.MockTransport(handle), sleep=lambda _s: None
    )
    with pytest.raises(ProviderResponseInvalidError) as exc_info:
        provider.latest_block()
    assert API_KEY not in str(exc_info.value)


def test_constructor_rejects_an_empty_key():
    with pytest.raises(ValueError, match="api_key"):
        TronGridProvider(api_key="")


# -- get_provider factory ----------------------------------------------------


def test_factory_fixture_mode_ignores_the_key():
    provider = get_provider(Chain.TRON, "fixture", fixture_id="growjoy_tron_trc20")
    assert isinstance(provider, FixtureProvider)


def test_factory_live_mode_without_a_key_is_a_configuration_error():
    with pytest.raises(ConfigurationError):
        get_provider(Chain.TRON, "live", api_key=None)


def test_factory_live_mode_on_an_unsupported_chain():
    with pytest.raises(UnsupportedChainError):
        get_provider(Chain.ETHEREUM, "live", api_key=API_KEY)


def test_factory_auto_mode_without_a_key_falls_back_to_fixture():
    provider = get_provider(Chain.TRON, "auto", fixture_id="growjoy_tron_trc20", api_key=None)
    assert isinstance(provider, FixtureProvider)


def test_factory_auto_mode_with_a_key_selects_live():
    provider = get_provider(Chain.TRON, "auto", api_key=API_KEY)
    assert isinstance(provider, TronGridProvider)


def test_factory_rejects_an_unknown_mode():
    with pytest.raises(ConfigurationError):
        get_provider(Chain.TRON, "bogus", api_key=API_KEY)
