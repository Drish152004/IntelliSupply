"""Load model bundles and run demand forecasting inference."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from .lade_demand import (
    FEATURE_COLS,
    build_daily_demand,
    build_multistep_forecast,
    default_model_dir,
    load_city_data,
    make_daily_panel,
)
from .lade_weekly import prepare_weekly_pipeline
from .weekly_strategies import produce_weekly_forecast

PACKAGE_DIR = Path(__file__).resolve().parent
MODELS_DIR = default_model_dir()

DEFAULT_FEATURE_COLS = FEATURE_COLS


def export_pkl_bundle(
    granularity: str = "daily",
    *,
    models_dir: Path | None = None,
) -> Path:
    """Export trained joblib model to a single .pkl bundle."""
    models_dir = models_dir or MODELS_DIR
    if granularity == "daily":
        joblib_path = models_dir / "lade_demand_forecaster.joblib"
        meta_path = models_dir / "lade_demand_forecaster.meta.json"
        pkl_path = models_dir / "lade_demand_forecaster.pkl"
    else:
        joblib_path = models_dir / f"lade_demand_forecaster_{granularity}.joblib"
        meta_path = models_dir / f"lade_demand_forecaster_{granularity}.meta.json"
        pkl_path = models_dir / f"lade_demand_forecaster_{granularity}.pkl"

    if not joblib_path.exists():
        raise FileNotFoundError(f"Train first — missing {joblib_path}")

    model = joblib.load(joblib_path)
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    bundle = {
        "granularity": granularity,
        "feature_cols": metadata.get("feature_cols", FEATURE_COLS),
        "metadata": metadata,
        "model": model,
    }
    with pkl_path.open("wb") as fh:
        pickle.dump(bundle, fh)
    return pkl_path


def load_pkl_bundle(pkl_path: Path | None = None) -> dict[str, Any]:
    pkl_path = pkl_path or MODELS_DIR / "lade_demand_forecaster.pkl"
    if not pkl_path.exists():
        raise FileNotFoundError(f"No bundle at {pkl_path}")
    with pkl_path.open("rb") as fh:
        return pickle.load(fh)


def load_bundle(pkl_name: str = "lade_demand_forecaster.pkl") -> dict[str, Any]:
    """Load .pkl bundle (used by FastAPI registry and standalone API)."""
    return load_pkl_bundle(MODELS_DIR / pkl_name)


def predict(
    records: list[dict[str, Any]],
    *,
    bundle: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run inference on pre-built feature rows."""
    return predict_from_features(records, bundle=bundle)


def predict_from_features(
    records: list[dict[str, Any]],
    *,
    bundle: dict[str, Any] | None = None,
    pkl_path: Path | None = None,
) -> list[dict[str, Any]]:
    if bundle is None:
        bundle = load_pkl_bundle(pkl_path)

    model: Pipeline = bundle["model"]
    feature_cols: list[str] = bundle.get("feature_cols", DEFAULT_FEATURE_COLS)
    frame = pd.DataFrame(records)

    missing = set(feature_cols) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing feature columns: {sorted(missing)}")

    preds = np.clip(model.predict(frame[feature_cols]), 0, None)
    results = []
    for i, pred in enumerate(preds):
        row = {
            k: records[i][k]
            for k in ("ds", "city", "region_id")
            if k in records[i]
        }
        row["predicted_demand"] = float(pred)
        results.append(row)
    return results


def forecast_demand(
    *,
    granularity: Literal["daily", "weekly"] = "daily",
    horizon: int = 7,
    city: str | None = None,
    dataset_kind: str = "delivery",
    weekly_strategy: str | None = None,
) -> pd.DataFrame:
    """End-to-end forecast from LaDe history."""
    bundle = load_pkl_bundle()
    model: Pipeline = bundle["model"]

    raw = load_city_data(dataset_kind)
    daily_panel = make_daily_panel(build_daily_demand(raw))

    if granularity == "daily":
        forecast = build_multistep_forecast(daily_panel, model, n_days=horizon)
    else:
        strategy_path = MODELS_DIR / "weekly_strategy.json"
        strategy = weekly_strategy or "daily_sum"
        if strategy_path.exists():
            strategy = json.loads(strategy_path.read_text(encoding="utf-8"))["recommended"]
        weekly_panel, _ = prepare_weekly_pipeline(dataset_kind)
        forecast = produce_weekly_forecast(
            strategy,  # type: ignore[arg-type]
            dataset_kind=dataset_kind,
            n_weeks=horizon,
            daily_panel=daily_panel,
            daily_model=model,
            weekly_panel=weekly_panel,
        )

    if city:
        forecast = forecast[forecast["city"] == city]
    return forecast
