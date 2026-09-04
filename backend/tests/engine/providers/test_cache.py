from __future__ import annotations

from app.engine.providers.cache import ResponseCache


def test_none_root_is_a_no_op_cache():
    cache = ResponseCache(None)
    assert cache.enabled is False
    cache.put("p", "e", {}, {"x": 1})
    assert cache.get("p", "e", {}) is None


def test_empty_string_root_is_treated_as_disabled_not_cwd():
    """AEGIS_PROVIDER_CACHE_DIR= (present but empty) must disable caching,
    not silently cache into the process's current directory."""
    cache = ResponseCache("")
    assert cache.enabled is False


def test_put_then_get_round_trips(tmp_path):
    cache = ResponseCache(tmp_path)
    assert cache.enabled is True
    assert cache.get("p", "e", {"a": 1}) is None
    cache.put("p", "e", {"a": 1}, {"result": "ok"})
    assert cache.get("p", "e", {"a": 1}) == {"result": "ok"}


def test_different_params_are_different_cache_keys(tmp_path):
    cache = ResponseCache(tmp_path)
    cache.put("p", "e", {"a": 1}, {"result": "first"})
    assert cache.get("p", "e", {"a": 2}) is None
