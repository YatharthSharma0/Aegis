"""The committed frontend demo data must match what the engine produces today."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_demo_data.py"


def test_frontend_demo_data_is_current() -> None:
    spec = importlib.util.spec_from_file_location("export_demo_data", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up here
    spec.loader.exec_module(module)

    assert module.OUTPUT.read_text(encoding="utf-8") == module.render(), (
        "regenerate with: uv run python scripts/export_demo_data.py"
    )
