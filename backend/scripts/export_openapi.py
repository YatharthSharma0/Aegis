"""Write the current FastAPI schema to backend/openapi.json.

The committed file is the source of truth the frontend generates its types from.
CI runs this and fails if the checked-in file is stale.

    uv run python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from app.main import app  # noqa: E402 — after sys.path setup

OUT = _BACKEND / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
