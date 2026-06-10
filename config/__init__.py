"""Shared configuration for IntelliSupply."""

from config.env import load_env
from config.ml_api import eta_model_path, route_model_path
from config.paths import (
    AGENTIC_ROOT,
    BACKEND_ROOT,
    CLUSTER_ASSIGNMENTS_PATH,
    DEMAND_FORECASTING_ROOT,
    DEMAND_HF_BUNDLE_PATH,
    ETA_MODEL_PATH,
    ETA_PREDICTION_ROOT,
    FASTAPI_ROOT,
    HF_SPACE_ROOT,
    MODELS_ROOT,
    ORDERS_CLUSTERED_PATH,
    RAG_ROOT,
    REPO_ROOT,
    ROUTE_MODEL_PATH,
    ROUTE_PREDICTION_ROOT,
)

__all__ = [
    "AGENTIC_ROOT",
    "BACKEND_ROOT",
    "CLUSTER_ASSIGNMENTS_PATH",
    "DEMAND_FORECASTING_ROOT",
    "DEMAND_HF_BUNDLE_PATH",
    "ETA_MODEL_PATH",
    "ETA_PREDICTION_ROOT",
    "FASTAPI_ROOT",
    "HF_SPACE_ROOT",
    "MODELS_ROOT",
    "ORDERS_CLUSTERED_PATH",
    "RAG_ROOT",
    "REPO_ROOT",
    "ROUTE_MODEL_PATH",
    "ROUTE_PREDICTION_ROOT",
    "eta_model_path",
    "load_env",
    "route_model_path",
]
