"""Paths and environment configuration for the unified ML API."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_PREDICTION_ROOT = REPO_ROOT / "ml_services" / "route_prediction"
DEMAND_FORECASTING_ROOT = REPO_ROOT / "ml_services" / "demand_forecasting"
ETA_PREDICTION_ROOT = REPO_ROOT / "ml_services" / "eta-prediction"
ETA_SRC_ROOT = ETA_PREDICTION_ROOT

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"

DEFAULT_ROUTE_MODEL = ROUTE_PREDICTION_ROOT / "notebooks" / "route_ranker.pkl"
DEFAULT_DEMAND_MODEL = DEMAND_FORECASTING_ROOT / "models" / "lade_demand_forecaster.pkl"


def route_model_path() -> Path:
    return Path(os.environ.get("ROUTE_RANKER_MODEL", DEFAULT_ROUTE_MODEL))


def demand_model_name() -> str:
    return os.environ.get("DEMAND_MODEL", "lade_demand_forecaster.pkl")
