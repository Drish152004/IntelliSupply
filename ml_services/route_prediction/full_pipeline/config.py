"""Paths and hyperparameters for the end-to-end delivery pipeline."""

from __future__ import annotations

from pathlib import Path

from config.paths import (
    CLUSTER_ASSIGNMENTS_PATH,
    ORDERS_CLUSTERED_PATH,
    ROUTE_MODEL_PATH,
)

PIPELINE_DIR = Path(__file__).resolve().parent

DATA_DIR = PIPELINE_DIR / "data"
OUTPUT_DIR = PIPELINE_DIR / "outputs"

EPS_KM = 0.5
EARTH_RADIUS_KM = 6371.0
EPS_RAD = EPS_KM / EARTH_RADIUS_KM

COURIER_TIE_BREAK_KM = 0.05
