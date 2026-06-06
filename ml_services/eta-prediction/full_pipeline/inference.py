"""ETA model loading, feature engineering, and inference."""

from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def _read_pickle_dataframe(path: Path) -> pd.DataFrame:
    """Load a pickled DataFrame without requiring pyarrow (pandas 3.x compat)."""
    with path.open("rb") as fh:
        obj = pickle.load(fh)
    if isinstance(obj, pd.DataFrame):
        return obj
    return pd.DataFrame(obj)


class ETARequest(BaseModel):
    delivery_user_id: int
    from_dipan_id: int
    aoi_id: int
    receipt_time: str
    receipt_lat: float
    receipt_lng: float
    poi_lat: float
    poi_lng: float


@lru_cache(maxsize=1)
def _load_artifacts() -> dict[str, Any]:
    model = pickle.load(open(MODELS_DIR / "lgbm_eta_model.pkl", "rb"))
    features = pickle.load(open(MODELS_DIR / "features.pkl", "rb"))
    cat_mappings = pickle.load(open(MODELS_DIR / "cat_mappings.pkl", "rb"))

    courier_stats = _read_pickle_dataframe(MODELS_DIR / "courier_stats.pkl")
    courier_daily = _read_pickle_dataframe(MODELS_DIR / "courier_daily.pkl")
    courier_hourly = _read_pickle_dataframe(MODELS_DIR / "courier_hourly.pkl")
    aoi_stats = _read_pickle_dataframe(MODELS_DIR / "aoi_stats.pkl")

    courier_stats["delivery_user_id"] = courier_stats["delivery_user_id"].astype(str)
    courier_daily["delivery_user_id"] = courier_daily["delivery_user_id"].astype(str)
    courier_hourly["delivery_user_id"] = courier_hourly["delivery_user_id"].astype(str)
    aoi_stats["aoi_id"] = aoi_stats["aoi_id"].astype(str)

    return {
        "model": model,
        "features": features,
        "cat_mappings": cat_mappings,
        "courier_stats": courier_stats,
        "courier_daily": courier_daily,
        "courier_hourly": courier_hourly,
        "aoi_stats": aoi_stats,
    }


def build_features(data: ETARequest | dict[str, Any], artifacts: dict[str, Any] | None = None) -> pd.DataFrame:
    if artifacts is None:
        artifacts = _load_artifacts()

    from full_pipeline.feature_engineering import build_features as bf
    return bf(data, artifacts)



def predict_eta(data: ETARequest | dict[str, Any]) -> dict[str, float]:
    artifacts = _load_artifacts()
    features = build_features(data, artifacts)
    pred = artifacts["model"].predict(features)[0]
    return {"eta_minutes": round(float(pred), 2)}
