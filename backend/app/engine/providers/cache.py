"""On-disk response cache for live providers.

Keyed by ``(provider, endpoint, params)`` — the exact request shape, not the
response — so a repeat of the same query against the same provider is a
cache hit regardless of process restarts. This is the Phase 4.5 mitigation
for making a rehearsed/repeated demo trace cost zero live calls after the
first run: nothing here is time-aware or invalidates on its own. Delete the
cache directory to force fresh calls.

Deliberately dumb (a file per key, whole-body JSON) — the response volumes a
single trace touches are small (tens to low hundreds of calls), and simplicity
here matters more than a real cache eviction policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.engine.canonical import canonical_json, sha256_hex


class ResponseCache:
    """A no-op cache when ``root`` is ``None`` — callers don't need to branch."""

    def __init__(self, root: str | Path | None) -> None:
        # An empty string (e.g. AEGIS_PROVIDER_CACHE_DIR= with no value) means
        # "disabled", same as None — not "cache in the current directory".
        self._root = Path(root) if root else None
        if self._root is not None:
            self._root.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._root is not None

    def _path(self, root: Path, provider: str, endpoint: str, params: dict[str, Any]) -> Path:
        key = sha256_hex(
            canonical_json({"provider": provider, "endpoint": endpoint, "params": params})
        )
        return root / f"{key}.json"

    def get(self, provider: str, endpoint: str, params: dict[str, Any]) -> Any | None:
        if self._root is None:
            return None
        path = self._path(self._root, provider, endpoint, params)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, provider: str, endpoint: str, params: dict[str, Any], response: Any) -> None:
        if self._root is None:
            return
        path = self._path(self._root, provider, endpoint, params)
        path.write_text(json.dumps(response), encoding="utf-8")
