"""Engine error taxonomy and non-exception trail outcomes.

Two distinct concepts:

* **Exceptions** (:class:`EngineError` and friends) — something went wrong that
  the caller must handle: a bad address, an unsupported chain, a provider that
  timed out or returned garbage.
* **Trail outcomes** (:class:`TrailLostReason`, :class:`PartialReason`) — the
  trace itself ran fine but a branch legitimately stopped: it hit a mixer, a
  bridge, the hop limit, the time budget. These are *data* in the result, never
  raised. The engine must emit one of these rather than inventing a continuation.
"""

from __future__ import annotations

from enum import StrEnum


class EngineError(Exception):
    """Base class for every exception the engine raises."""


class ConfigurationError(EngineError):
    """The engine or a provider was configured incorrectly (missing key, etc.)."""


class UnsupportedChainError(EngineError):
    """A chain the engine has no adapter for was requested."""


class UnsupportedAssetError(EngineError):
    """An asset/token the active adapter cannot decode was requested."""


class AddressFormatError(EngineError):
    """An address failed chain-specific format/checksum validation."""


class FixtureError(EngineError):
    """A recorded fixture is missing, malformed, or failed its checksum."""


class ProviderError(EngineError):
    """A chain-data provider call failed. Subclasses name the failure mode."""


class ProviderTimeoutError(ProviderError):
    """The provider did not respond within the configured timeout."""


class ProviderRateLimitedError(ProviderError):
    """The provider signalled a rate limit (e.g. HTTP 429)."""


class ProviderUnavailableError(ProviderError):
    """The provider is unreachable or returned a 5xx / transport error."""


class ProviderResponseInvalidError(ProviderError):
    """The provider responded but the payload could not be parsed/validated."""


class TrailLostReason(StrEnum):
    """Why a branch of the forward walk stopped without reaching an endpoint."""

    PROVIDER_EXHAUSTED = "provider_exhausted"
    RATE_LIMITED = "rate_limited"
    UNSUPPORTED_CONTRACT = "unsupported_contract"
    BRIDGE = "bridge"
    MIXER_LIKE = "mixer_like"
    MAX_HOPS = "max_hops"
    MIN_VALUE = "min_value"
    MIN_TAINT = "min_taint"
    DEADLINE = "deadline"
    CYCLE = "cycle"


class PartialReason(StrEnum):
    """Why a whole trace finished in a ``partial`` rather than ``done`` state."""

    DEADLINE = "deadline"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    NODE_BUDGET = "node_budget"
    EDGE_BUDGET = "edge_budget"
