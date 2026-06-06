"""
LaDe demand forecasting by city, region_id, and date.

Raw LaDe columns used
---------------------
From delivery_*.csv / pickup_*.csv we only need:
  - ds         : calendar day (MMDD encoded in source files)
  - city       : city name
  - region_id  : spatial zone for aggregation

Each row is one package/task. Daily demand = count of rows per (ds, city, region_id).

Engineered features (model inputs)
----------------------------------
  - city, region_id (one-hot encoded)
  - day_of_week, month, day_of_month, day_of_year, is_weekend
  - lag_1, lag_2, lag_7, lag_14
  - rolling_mean_7, rolling_std_7, rolling_mean_28

Target: demand (non-negative integer count).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

FEATURE_COLS = [
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

LADE_RAW_COLUMNS = ["ds", "city", "region_id"]


def project_root() -> Path:
    """Repository root (parent of ``ml_services/``)."""
    return Path(__file__).resolve().parents[2]


def default_lade_dir() -> Path:
    import os

    override = os.environ.get("LADE_DATA_DIR")
    if override:
        return Path(override)
    return project_root() / "LaDe"


def default_model_dir() -> Path:
    return Path(__file__).resolve().parent / "models"


def parse_lade_ds(values: pd.Series) -> pd.DatetimeIndex:
    cleaned = values.astype(str).str.replace(r"\D", "", regex=True).str.zfill(4)
    month = cleaned.str[:2].astype(int)
    day = cleaned.str[2:].astype(int)
    return pd.to_datetime({"year": 2024, "month": month, "day": day}, errors="coerce")


def find_city_files(lade_dir: Path, dataset_kind: str) -> list[Path]:
    folder = lade_dir / dataset_kind
    return sorted(folder.glob(f"{dataset_kind}_*.csv"))


def load_city_data(
    dataset_kind: str = "delivery",
    lade_dir: Path | None = None,
) -> pd.DataFrame:
    lade_dir = lade_dir or default_lade_dir()
    files = find_city_files(lade_dir, dataset_kind)
    if not files:
        raise FileNotFoundError(f"No {dataset_kind} CSV files in {lade_dir / dataset_kind}")

    frames = []
    for path in files:
        frame = pd.read_csv(path, usecols=LADE_RAW_COLUMNS, low_memory=False)
        frame["source_file"] = path.name
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    data["ds"] = parse_lade_ds(data["ds"])
    data = data.dropna(subset=["ds", "city", "region_id"])
    data["city"] = data["city"].astype(str)
    data["region_id"] = data["region_id"].astype(str)
    return data


def build_daily_demand(raw: pd.DataFrame) -> pd.DataFrame:
    return (
        raw.groupby(["ds", "city", "region_id"], as_index=False)
        .size()
        .rename(columns={"size": "demand"})
        .sort_values(["city", "region_id", "ds"])
    )


def make_daily_panel(daily_counts: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for (city, region_id), group in daily_counts.groupby(["city", "region_id"]):
        group = group.sort_values("ds").set_index("ds")
        full_index = pd.date_range(group.index.min(), group.index.max(), freq="D")
        group = group.reindex(full_index)
        group.index.name = "ds"
        group = group.assign(city=city, region_id=region_id)
        group["demand"] = group["demand"].fillna(0)
        parts.append(group.reset_index())

    panel = pd.concat(parts, ignore_index=True)
    panel["demand"] = panel["demand"].astype(float)
    return panel.sort_values(["city", "region_id", "ds"]).reset_index(drop=True)


def add_features(panel: pd.DataFrame) -> pd.DataFrame:
    enriched = panel.copy()
    enriched["day_of_week"] = enriched["ds"].dt.dayofweek
    enriched["month"] = enriched["ds"].dt.month
    enriched["day_of_month"] = enriched["ds"].dt.day
    enriched["day_of_year"] = enriched["ds"].dt.dayofyear
    enriched["is_weekend"] = (enriched["day_of_week"] >= 5).astype(int)

    enriched = enriched.sort_values(["city", "region_id", "ds"])
    grouped = enriched.groupby(["city", "region_id"], group_keys=False)

    for lag in (1, 2, 7, 14):
        enriched[f"lag_{lag}"] = grouped["demand"].transform(lambda s: s.shift(lag))

    enriched["rolling_mean_7"] = grouped["demand"].transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).mean()
    )
    enriched["rolling_std_7"] = grouped["demand"].transform(
        lambda s: s.shift(1).rolling(7, min_periods=2).std()
    )
    enriched["rolling_mean_28"] = grouped["demand"].transform(
        lambda s: s.shift(1).rolling(28, min_periods=1).mean()
    )
    return enriched


def model_ready_frame(featured: pd.DataFrame) -> pd.DataFrame:
    required = ["lag_1", "lag_2", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_28"]
    return featured.dropna(subset=required).copy()


def build_model_pipeline(
    *,
    feature_cols: list[str] | None = None,
    max_depth: int = 10,
    learning_rate: float = 0.06,
    max_iter: int = 400,
    random_state: int = 42,
) -> Pipeline:
    feature_cols = feature_cols or FEATURE_COLS
    categorical_features = [c for c in ("city", "region_id") if c in feature_cols]
    numeric_features = [col for col in feature_cols if col not in categorical_features]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_features,
            ),
            ("num", SimpleImputer(strategy="median"), numeric_features),
        ]
    )

    return Pipeline(
        steps=[
            ("prep", preprocessor),
            (
                "reg",
                HistGradientBoostingRegressor(
                    max_depth=max_depth,
                    learning_rate=learning_rate,
                    max_iter=max_iter,
                    min_samples_leaf=20,
                    l2_regularization=0.1,
                    random_state=random_state,
                ),
            ),
        ]
    )


def split_holdout(model_data: pd.DataFrame, holdout_days: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff = model_data["ds"].max() - pd.Timedelta(days=holdout_days)
    train = model_data[model_data["ds"] <= cutoff].copy()
    test = model_data[model_data["ds"] > cutoff].copy()
    return train, test


def _safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def evaluate_holdout(
    model: Pipeline,
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> dict[str, float]:
    model.fit(train[FEATURE_COLS], train["demand"])
    pred = np.clip(model.predict(test[FEATURE_COLS]), 0, None)
    y = test["demand"].values
    return {
        "mae": float(mean_absolute_error(y, pred)),
        "rmse": float(root_mean_squared_error(y, pred)),
        "mape": _safe_mape(y, pred),
        "r2": float(r2_score(y, pred)),
    }


def train_final_model(model_data: pd.DataFrame) -> Pipeline:
    model = build_model_pipeline()
    model.fit(model_data[FEATURE_COLS], model_data["demand"])
    return model


def build_multistep_forecast(
    history_panel: pd.DataFrame,
    model_pipeline: Pipeline,
    feature_cols: list[str] | None = None,
    n_days: int = 7,
) -> pd.DataFrame:
    feature_cols = feature_cols or FEATURE_COLS
    forecast_rows: list[pd.DataFrame] = []
    extended_history = history_panel[["ds", "city", "region_id", "demand"]].copy()
    last_date = extended_history["ds"].max()

    for step in range(1, n_days + 1):
        forecast_date = last_date + pd.Timedelta(days=step)
        step_predictions: list[dict[str, Any]] = []

        for (city, region_id), group in extended_history.groupby(["city", "region_id"]):
            group = group.sort_values("ds")
            values = group["demand"].tolist()
            if len(values) < 1:
                continue

            row = {
                "ds": forecast_date,
                "city": city,
                "region_id": region_id,
                "day_of_week": forecast_date.dayofweek,
                "month": forecast_date.month,
                "day_of_month": forecast_date.day,
                "day_of_year": forecast_date.dayofyear,
                "is_weekend": int(forecast_date.dayofweek >= 5),
                "lag_1": values[-1],
                "lag_2": values[-2] if len(values) >= 2 else values[-1],
                "lag_7": values[-7] if len(values) >= 7 else float(np.mean(values)),
                "lag_14": values[-14] if len(values) >= 14 else float(np.mean(values)),
                "rolling_mean_7": float(np.mean(values[-7:])),
                "rolling_std_7": float(np.std(values[-7:], ddof=1)) if len(values[-7:]) > 1 else 0.0,
                "rolling_mean_28": float(np.mean(values[-28:])),
            }
            step_predictions.append(row)

        step_df = pd.DataFrame(step_predictions)
        step_df["predicted_demand"] = np.clip(model_pipeline.predict(step_df[feature_cols]), 0, None)
        forecast_rows.append(step_df[["ds", "city", "region_id", "predicted_demand"]])

        new_rows = step_df[["ds", "city", "region_id", "predicted_demand"]].rename(
            columns={"predicted_demand": "demand"}
        )
        extended_history = pd.concat([extended_history, new_rows], ignore_index=True)

    return pd.concat(forecast_rows, ignore_index=True)


def artifact_paths(granularity: str = "daily") -> tuple[Path, Path]:
    model_dir = default_model_dir()
    if granularity == "daily":
        return (
            model_dir / "lade_demand_forecaster.joblib",
            model_dir / "lade_demand_forecaster.meta.json",
        )
    return (
        model_dir / f"lade_demand_forecaster_{granularity}.joblib",
        model_dir / f"lade_demand_forecaster_{granularity}.meta.json",
    )


def save_artifact(
    model: Pipeline,
    panel: pd.DataFrame,
    *,
    dataset_kind: str,
    granularity: str = "daily",
    feature_cols: list[str] | None = None,
    model_path: Path | None = None,
    metadata_path: Path | None = None,
    holdout_metrics: dict[str, float] | None = None,
    forecast_horizon: int | None = None,
) -> tuple[Path, Path]:
    model_dir = default_model_dir()
    model_dir.mkdir(parents=True, exist_ok=True)
    default_model, default_meta = artifact_paths(granularity)
    model_path = model_path or default_model
    metadata_path = metadata_path or default_meta

    joblib.dump(model, model_path)

    metadata = {
        "granularity": granularity,
        "dataset_kind": dataset_kind,
        "feature_cols": feature_cols or FEATURE_COLS,
        "lade_raw_columns": LADE_RAW_COLUMNS,
        "last_history_date": str(panel["ds"].max().date()),
        "cities": sorted(panel["city"].unique().tolist()),
        "n_regions": int(panel["region_id"].nunique()),
        "holdout_metrics": holdout_metrics or {},
        "default_forecast_horizon": forecast_horizon,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return model_path, metadata_path


def load_artifact(
    granularity: str = "daily",
    model_path: Path | None = None,
    metadata_path: Path | None = None,
) -> tuple[Pipeline, dict[str, Any]]:
    default_model, default_meta = artifact_paths(granularity)
    model_path = model_path or default_model
    metadata_path = metadata_path or default_meta

    if not model_path.exists():
        raise FileNotFoundError(f"No saved model at {model_path}. Run scripts/train_demand_model.py first.")

    model = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return model, metadata


def forecast_from_saved(
    history_panel: pd.DataFrame | None = None,
    *,
    dataset_kind: str = "delivery",
    n_days: int = 7,
    lade_dir: Path | None = None,
) -> pd.DataFrame:
    """Load saved daily model and produce n-day regional forecast."""
    model, _meta = load_artifact("daily")
    if history_panel is None:
        raw = load_city_data(dataset_kind, lade_dir=lade_dir)
        daily = build_daily_demand(raw)
        history_panel = make_daily_panel(daily)
    return build_multistep_forecast(history_panel, model, n_days=n_days)
