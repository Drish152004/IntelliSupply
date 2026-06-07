"""Shared configuration for IntelliSupply."""

from config.env import load_env
from config.ml_api import demand_model_name, route_model_path
from config.paths import (
    AGENTIC_ROOT,
    BACKEND_ROOT,
    CLUSTER_ASSIGNMENTS_PATH,
    DEFAULT_DEMAND_MODEL,
    DEMAND_FORECASTING_ROOT,
    ETA_PREDICTION_ROOT,
    ETA_SRC_ROOT,
    FASTAPI_ROOT,
    NOTEBOOK_OUTPUTS_DIR,
    ORDERS_CLUSTERED_PATH,
    RAG_ROOT,
    REPO_ROOT,
    ROUTE_MODEL_PATH,
    ROUTE_NOTEBOOKS_DIR,
    ROUTE_PREDICTION_ROOT,
)

__all__ = [
    "AGENTIC_ROOT",
    "BACKEND_ROOT",
    "CLUSTER_ASSIGNMENTS_PATH",
    "DEFAULT_DEMAND_MODEL",
    "DEMAND_FORECASTING_ROOT",
    "ETA_PREDICTION_ROOT",
    "ETA_SRC_ROOT",
    "FASTAPI_ROOT",
    "NOTEBOOK_OUTPUTS_DIR",
    "ORDERS_CLUSTERED_PATH",
    "RAG_ROOT",
    "REPO_ROOT",
    "ROUTE_MODEL_PATH",
    "ROUTE_NOTEBOOKS_DIR",
    "ROUTE_PREDICTION_ROOT",
    "demand_model_name",
    "load_env",
    "route_model_path",
]
