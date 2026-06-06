"""Paths and defaults for the end-to-end demand forecasting pipeline."""

from __future__ import annotations

from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = PIPELINE_DIR.parent
REPO_ROOT = PACKAGE_DIR.parents[1]

LADE_DIR = REPO_ROOT / "LaDe"
MODELS_DIR = PACKAGE_DIR / "models"
OUTPUT_DIR = PIPELINE_DIR / "outputs"

DAILY_MODEL_PATH = MODELS_DIR / "lade_demand_forecaster.joblib"
DAILY_META_PATH = MODELS_DIR / "lade_demand_forecaster.meta.json"
PKL_BUNDLE_PATH = MODELS_DIR / "lade_demand_forecaster.pkl"
WEEKLY_STRATEGY_PATH = MODELS_DIR / "weekly_strategy.json"

DEFAULT_DATASET_KIND = "delivery"
DEFAULT_DAILY_HORIZON = 7
DEFAULT_WEEKLY_HORIZON = 4
DEFAULT_WEEKLY_STRATEGY = "daily_sum"
