"""Lazy-loaded singletons for all ML services."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from config import (
    DEMAND_FORECASTING_ROOT,
    ETA_SRC_ROOT,
    ROUTE_PREDICTION_ROOT,
    demand_model_name,
    route_model_path,
)

_route_predictor: Any | None = None
_demand_bundle: dict[str, Any] | None = None
_eta_ready: bool = False


def _ensure_route_path() -> None:
    path = str(ROUTE_PREDICTION_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


def _ensure_demand_path() -> None:
    path = str(DEMAND_FORECASTING_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


def _ensure_eta_path() -> None:
    path = str(ETA_SRC_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


def get_route_predictor():
    global _route_predictor
    if _route_predictor is None:
        _ensure_route_path()
        from route_predictor import RoutePredictor

        model_path = route_model_path()
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Route model not found: {model_path}. Set ROUTE_RANKER_MODEL or train the model."
            )
        _route_predictor = RoutePredictor.load(model_path)
    return _route_predictor


def get_demand_bundle() -> dict[str, Any]:
    global _demand_bundle
    if _demand_bundle is None:
        _ensure_demand_path()
        from inference import load_bundle

        _demand_bundle = load_bundle(demand_model_name())
    return _demand_bundle


def init_eta_service() -> None:
    global _eta_ready
    _ensure_eta_path()
    from eta_inference import _load_artifacts

    _load_artifacts()
    _eta_ready = True


def ensure_eta_service() -> None:
    if not _eta_ready:
        init_eta_service()


def init_all_services() -> dict[str, str]:
    """Warm all models; returns per-service status messages."""
    status: dict[str, str] = {}
    try:
        get_route_predictor()
        status["route_prediction"] = "ok"
    except Exception as exc:
        status["route_prediction"] = f"error: {exc}"

    try:
        get_demand_bundle()
        status["demand_forecasting"] = "ok"
    except Exception as exc:
        status["demand_forecasting"] = f"error: {exc}"

    try:
        init_eta_service()
        status["eta_prediction"] = "ok"
    except Exception as exc:
        status["eta_prediction"] = f"error: {exc}"

    return status
