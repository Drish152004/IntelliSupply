"""
Bridge from LangGraph agents to unified ML inference (FastAPI/services).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from config.paths import FASTAPI_ROOT, REPO_ROOT

_AGENTIC_ROOT = Path(__file__).resolve().parents[1]


def _ensure_fastapi_path() -> None:
    """Put FastAPI/ first and drop agentic_ai from path to avoid `services` name clash."""
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


def run_eta_prediction(payload: dict[str, Any]) -> dict[str, Any]:
    eta = _load_fastapi_module("services/eta_prediction.py")
    return eta.predict_eta(payload)


def run_route_next_stop(payload: dict[str, Any]) -> dict[str, Any]:
    route = _load_fastapi_module("services/route_prediction.py")
    return route.predict_next_stop(payload)


def run_route_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    route = _load_fastapi_module("services/route_prediction.py")
    return route.predict_route_sequence(payload)


def run_demand_prediction(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Call hosted demand model on Hugging Face (via FastAPI demand service)."""
    demand = _load_fastapi_module("services/demand_forecasting.py")
    return demand.predict_demand(records)
