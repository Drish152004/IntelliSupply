"""ML API path helpers (formerly FastAPI/config.py)."""

from __future__ import annotations

import os
from pathlib import Path

from config.paths import DEFAULT_DEMAND_MODEL, ROUTE_MODEL_PATH

DEFAULT_ROUTE_MODEL = ROUTE_MODEL_PATH


def route_model_path() -> Path:
    return Path(os.environ.get("ROUTE_RANKER_MODEL", DEFAULT_ROUTE_MODEL))


def demand_model_name() -> str:
    return os.environ.get("DEMAND_MODEL", DEFAULT_DEMAND_MODEL.name)
