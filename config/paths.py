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

MODELS_ROOT = REPO_ROOT / "models"
ROUTE_MODEL_PATH = MODELS_ROOT / "route_ranker.pkl"
ETA_MODEL_PATH = MODELS_ROOT / "eta_lightgbm_model.pkl"
DEMAND_HF_BUNDLE_PATH = MODELS_ROOT / "lade_demand_forecaster.pkl"
HF_SPACE_ROOT = MODELS_ROOT / "hf_space"
CLUSTER_ASSIGNMENTS_PATH = MODELS_ROOT / "cluster_assignments.csv"
ORDERS_CLUSTERED_PATH = MODELS_ROOT / "orders_clustered.csv"

ENV_FILE = REPO_ROOT / ".env"
