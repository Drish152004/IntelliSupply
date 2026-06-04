"""Paths and hyperparameters for the end-to-end delivery pipeline."""

from __future__ import annotations

from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
ROUTE_PREDICTION_DIR = PIPELINE_DIR.parent
REPO_ROOT = ROUTE_PREDICTION_DIR.parents[1]

DATA_DIR = PIPELINE_DIR / "data"
OUTPUT_DIR = PIPELINE_DIR / "outputs"

NOTEBOOK_OUTPUTS = ROUTE_PREDICTION_DIR / "notebooks" / "outputs"
CLUSTER_ASSIGNMENTS_PATH = NOTEBOOK_OUTPUTS / "cluster_assignments.csv"
ORDERS_CLUSTERED_PATH = NOTEBOOK_OUTPUTS / "orders_clustered.csv"
ROUTE_MODEL_PATH = ROUTE_PREDICTION_DIR / "notebooks" / "route_ranker.pkl"

EPS_KM = 0.5
EARTH_RADIUS_KM = 6371.0
EPS_RAD = EPS_KM / EARTH_RADIUS_KM

COURIER_TIE_BREAK_KM = 0.05
