"""Load .pkl model bundle and run inference (no LaDe data required)."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

PACKAGE_DIR = Path(__file__).resolve().parent


def _bundle_path(pkl_name: str) -> Path:
    flat = PACKAGE_DIR.parent / pkl_name
    nested = PACKAGE_DIR / "models" / pkl_name
    if flat.exists():
        return flat
    return nested

DEFAULT_FEATURE_COLS = [
    "city",
    "region_id",
    "day_of_week",
    "month",
    "day_of_month",
    "day_of_year",
    "is_weekend",
    "lag_1",
    "lag_2",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_std_7",
    "rolling_mean_28",
]


def load_bundle(pkl_name: str = "lade_demand_forecaster.pkl") -> dict[str, Any]:
    pkl_path = _bundle_path(pkl_name)
    if not pkl_path.exists():
        raise FileNotFoundError(f"Model not found: {pkl_path}")
    with pkl_path.open("rb") as fh:
        return pickle.load(fh)


def predict(records: list[dict[str, Any]], *, bundle: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if bundle is None:
        bundle = load_bundle()

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
