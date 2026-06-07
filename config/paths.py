"""Canonical paths for IntelliSupply."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAG_ROOT = REPO_ROOT / "rag"
FASTAPI_ROOT = REPO_ROOT / "FastAPI"
AGENTIC_ROOT = REPO_ROOT / "agentic_ai"
BACKEND_ROOT = REPO_ROOT / "backend"

ROUTE_PREDICTION_ROOT = REPO_ROOT / "ml_services" / "route_prediction"
DEMAND_FORECASTING_ROOT = REPO_ROOT / "ml_services" / "demand_forecasting"
ETA_PREDICTION_ROOT = REPO_ROOT / "ml_services" / "eta-prediction"
ETA_SRC_ROOT = ETA_PREDICTION_ROOT

ROUTE_NOTEBOOKS_DIR = REPO_ROOT / "notebooks" / "route_prediction"
NOTEBOOK_OUTPUTS_DIR = ROUTE_NOTEBOOKS_DIR / "outputs"
ROUTE_MODEL_PATH = ROUTE_NOTEBOOKS_DIR / "route_ranker.pkl"
CLUSTER_ASSIGNMENTS_PATH = NOTEBOOK_OUTPUTS_DIR / "cluster_assignments.csv"
ORDERS_CLUSTERED_PATH = NOTEBOOK_OUTPUTS_DIR / "orders_clustered.csv"

DEFAULT_DEMAND_MODEL = DEMAND_FORECASTING_ROOT / "models" / "lade_demand_forecaster.pkl"

ENV_FILE = REPO_ROOT / ".env"
