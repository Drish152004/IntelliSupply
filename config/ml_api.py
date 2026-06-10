"""ML API path helpers (formerly FastAPI/config.py)."""

from __future__ import annotations

import os
from pathlib import Path

from config.paths import ETA_MODEL_PATH, ROUTE_MODEL_PATH

DEFAULT_ROUTE_MODEL = ROUTE_MODEL_PATH
DEFAULT_ETA_MODEL = ETA_MODEL_PATH


def route_model_path() -> Path:
    return Path(os.environ.get("ROUTE_RANKER_MODEL", DEFAULT_ROUTE_MODEL))


def eta_model_path() -> Path:
    return Path(os.environ.get("ETA_MODEL_PATH", DEFAULT_ETA_MODEL))
