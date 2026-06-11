"""Paths and hyperparameters for the end-to-end delivery pipeline."""

from __future__ import annotations

from pathlib import Path

from config.paths import ROUTE_MODEL_PATH

PIPELINE_DIR = Path(__file__).resolve().parent

DATA_DIR = PIPELINE_DIR / "data"
OUTPUT_DIR = PIPELINE_DIR / "outputs"
