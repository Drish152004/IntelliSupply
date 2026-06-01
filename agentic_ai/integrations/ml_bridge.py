"""
Bridge from LangGraph agents to unified ML inference (fastapi/services).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FASTAPI_ROOT = REPO_ROOT / "fastapi"
SAMPLES_DIR = FASTAPI_ROOT / "samples"
_AGENTIC_ROOT = Path(__file__).resolve().parents[1]


def _ensure_fastapi_path() -> None:
    """Put fastapi/ first and drop agentic_ai from path to avoid `services` name clash."""
    fastapi_path = str(FASTAPI_ROOT)
    agentic_path = str(_AGENTIC_ROOT.parent)

    if agentic_path in sys.path:
        sys.path.remove(agentic_path)
    if fastapi_path in sys.path:
        sys.path.remove(fastapi_path)
    sys.path.insert(0, fastapi_path)


def _load_fastapi_module(relative_path: str):
    _ensure_fastapi_path()
    module_path = FASTAPI_ROOT / relative_path
    module_name = "_intellisupply_" + relative_path.replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_sample(filename: str) -> dict[str, Any]:
    return json.loads((SAMPLES_DIR / filename).read_text(encoding="utf-8"))


def run_eta_prediction(payload: dict[str, Any]) -> dict[str, Any]:
    eta = _load_fastapi_module("services/eta_prediction.py")
    return eta.predict_eta(payload)


def run_route_next_stop(payload: dict[str, Any]) -> dict[str, Any]:
    route = _load_fastapi_module("services/route_prediction.py")
    return route.predict_next_stop(payload)


def run_route_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    route = _load_fastapi_module("services/route_prediction.py")
    return route.predict_route_sequence(payload)
