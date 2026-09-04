"""The durable trace worker.

Claims ``queued`` (and lease-expired ``running``) trace rows one at a time,
executes the Phase 1 engine, and persists the terminal state. Runs either
in-process (``AEGIS_TRACE_WORKER=inline``, the default — a daemon thread started
by the app lifespan) or as a separate process (``external`` + ``python -m
app.worker``, the Compose ``worker`` service). Same code both ways, so the
durability guarantees hold regardless.
"""

from app.worker.runner import TraceWorker

__all__ = ["TraceWorker"]
