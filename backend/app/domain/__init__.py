"""Domain layer: the trace lifecycle, independent of transport and storage.

* :mod:`app.domain.errors` — typed domain errors carrying an HTTP status + code.
* :mod:`app.domain.store` — the ``InvestigationStore`` interface and an
  in-memory implementation (Postgres swaps in behind the same interface).
* :mod:`app.domain.service` — ``TraceService``: start a trace, run it, read it.
* :mod:`app.domain.schemas` — the API request/response shapes (API contract),
  kept separate from the engine's ``app.engine.result`` types.
"""
