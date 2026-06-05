"""Feature engineering and stats computation module."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def compute_and_save_stats(df: pd.DataFrame, models_dir: Path = MODELS_DIR) -> dict[str, pd.DataFrame]:
    """Compute historical aggregates for couriers and AOIs, and save as pickles."""
    print("Computing stats...")
    
    # 1. Courier stats
    courier_stats = df.groupby("delivery_user_id").agg(
        courier_avg_eta=("eta_minutes", "mean"),
        courier_order_count=("eta_minutes", "count"),
        avg_distance=("distance_km", "mean")
    ).reset_index()

    courier_stats["historical_speed"] = (
        courier_stats["avg_distance"] / (courier_stats["courier_avg_eta"] + 1e-6)
    )

    # 2. Time-aware load
    courier_daily = df.groupby(
        ["delivery_user_id", "ds"]
    ).size().reset_index(name="courier_daily_load")

    courier_hourly = df.groupby(
        ["delivery_user_id", "ds", "hour"]
    ).size().reset_index(name="courier_hourly_load")

    # 3. AOI stats
    aoi_stats = df.groupby("aoi_id").agg(
        aoi_mean_eta=("eta_minutes", "mean"),
        aoi_count=("eta_minutes", "count"),
        aoi_avg_distance=("distance_km", "mean")
    ).reset_index()

    # Convert ID columns to strings for exact compatibility with inference
    courier_stats["delivery_user_id"] = courier_stats["delivery_user_id"].astype(str)
    courier_daily["delivery_user_id"] = courier_daily["delivery_user_id"].astype(str)
    courier_hourly["delivery_user_id"] = courier_hourly["delivery_user_id"].astype(str)
    aoi_stats["aoi_id"] = aoi_stats["aoi_id"].astype(str)

    # Save to pickles
    models_dir.mkdir(parents=True, exist_ok=True)
    courier_stats.to_pickle(models_dir / "courier_stats.pkl")
    aoi_stats.to_pickle(models_dir / "aoi_stats.pkl")
    courier_daily.to_pickle(models_dir / "courier_daily.pkl")
    courier_hourly.to_pickle(models_dir / "courier_hourly.pkl")
    
    print(f"Pickled stats saved to {models_dir}")
    
    return {
        "courier_stats": courier_stats,
        "courier_daily": courier_daily,
        "courier_hourly": courier_hourly,
        "aoi_stats": aoi_stats,
    }


def build_features(data: Any, artifacts: dict[str, Any]) -> pd.DataFrame:
    """Build inference/training features dynamically.
    
    Accepts Pydantic model, dictionary (for single row inference), or DataFrame (for bulk training).
    """
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        df = pd.DataFrame([payload])

    df["delivery_user_id"] = df["delivery_user_id"].astype(str)
    df["from_dipan_id"] = df["from_dipan_id"].astype(str)
    df["aoi_id"] = df["aoi_id"].astype(str)

    df["receipt_time"] = pd.to_datetime(df["receipt_time"])
    df["hour"] = df["receipt_time"].dt.hour
    df["weekday"] = df["receipt_time"].dt.weekday
    df["ds"] = df["receipt_time"].dt.dayofyear

    # Correct scale of distance calculation: degree coordinates * 111 km/degree
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
