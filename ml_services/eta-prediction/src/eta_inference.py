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

    payload = data.model_dump() if isinstance(data, ETARequest) else dict(data)
    df = pd.DataFrame([payload])

    df["delivery_user_id"] = df["delivery_user_id"].astype(str)
    df["from_dipan_id"] = df["from_dipan_id"].astype(str)
    df["aoi_id"] = df["aoi_id"].astype(str)

    df["receipt_time"] = pd.to_datetime(df["receipt_time"])
    df["hour"] = df["receipt_time"].dt.hour
    df["weekday"] = df["receipt_time"].dt.weekday
    df["ds"] = df["receipt_time"].dt.dayofyear

    df["distance_km"] = np.sqrt(
        (df["receipt_lat"] - df["poi_lat"]) ** 2 + (df["receipt_lng"] - df["poi_lng"]) ** 2
    ) * 111
    df["distance_hour_interaction"] = df["distance_km"] * df["hour"]

    courier_stats = artifacts["courier_stats"]
    courier_daily = artifacts["courier_daily"]
    courier_hourly = artifacts["courier_hourly"]
    aoi_stats = artifacts["aoi_stats"]
    cat_mappings = artifacts["cat_mappings"]
    features = artifacts["features"]

    df = df.merge(
        courier_stats[["delivery_user_id", "courier_avg_eta", "courier_order_count"]],
        on="delivery_user_id",
        how="left",
    )
    df = df.merge(courier_daily, on=["delivery_user_id", "ds"], how="left")
    df = df.merge(courier_hourly, on=["delivery_user_id", "ds", "hour"], how="left")
    df = df.merge(aoi_stats[["aoi_id", "aoi_mean_eta", "aoi_count"]], on="aoi_id", how="left")

    mean_eta = courier_stats["courier_avg_eta"].mean()
    df["courier_hourly_load"] = df["courier_hourly_load"].fillna(0)
    df["courier_daily_load"] = df["courier_daily_load"].fillna(0)
    df["courier_avg_eta"] = df["courier_avg_eta"].fillna(mean_eta)
    df["courier_order_count"] = df["courier_order_count"].fillna(0)
    df = df.fillna(0)

    for col in ["aoi_id", "delivery_user_id", "from_dipan_id"]:
        if col in df.columns:
            categories = cat_mappings.get(col, []) + ["missing"]
            df[col] = pd.Categorical(df[col], categories=categories)
            df[col] = df[col].fillna("missing")

    for col in features:
        if col not in df.columns:
            df[col] = 0

    return df[features]


def predict_eta(data: ETARequest | dict[str, Any]) -> dict[str, float]:
    artifacts = _load_artifacts()
    features = build_features(data, artifacts)
    pred = artifacts["model"].predict(features)[0]
    return {"eta_minutes": round(float(pred), 2)}
