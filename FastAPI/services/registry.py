"""Lazy-loaded singletons for all ML services."""

from __future__ import annotations

import sys
from typing import Any

from config import (
    ETA_PREDICTION_ROOT,
    ROUTE_PREDICTION_ROOT,
    eta_model_path,
    route_model_path,
)

_route_predictor: Any | None = None
_eta_predictor: Any | None = None
_eta_ready: bool = False


def _ensure_route_path() -> None:
    path = str(ROUTE_PREDICTION_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


def _ensure_eta_path() -> None:
    path = str(ETA_PREDICTION_ROOT)
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


def get_eta_predictor():
    global _eta_predictor
    if _eta_predictor is None:
        _ensure_eta_path()
        from full_pipeline.inference import ETAPredictor

        model_path = eta_model_path()
        if not model_path.is_file():
            raise FileNotFoundError(
                f"ETA model not found: {model_path}. Set ETA_MODEL_PATH or train the model."
            )
        _eta_predictor = ETAPredictor.load(model_path)
    return _eta_predictor


def init_demand_service() -> None:
    from services import demand_forecasting as demand_svc

    demand_svc.check_health()


def init_eta_service() -> None:
    global _eta_ready
    get_eta_predictor()
    _eta_ready = True


def ensure_eta_service() -> None:
    get_eta_predictor()


def init_all_services() -> dict[str, str]:
    """Warm all models; returns per-service status messages."""
    status: dict[str, str] = {}
    try:
        get_route_predictor()
        status["route_prediction"] = "ok"
    except Exception as exc:
        status["route_prediction"] = f"error: {exc}"

    try:
        init_demand_service()
        status["demand_forecasting"] = "ok"
    except Exception as exc:
        status["demand_forecasting"] = f"error: {exc}"

    try:
        init_eta_service()
        status["eta_prediction"] = "ok"
    except Exception as exc:
        status["eta_prediction"] = f"error: {exc}"

    return status
