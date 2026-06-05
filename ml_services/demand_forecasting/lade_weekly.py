"""Weekly demand forecasting (city + region_id + week)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from .lade_demand import (
    _safe_mape,
    build_daily_demand,
    build_model_pipeline,
    evaluate_holdout,
    load_artifact,
    load_city_data,
    save_artifact,
    train_final_model,
)

WEEKLY_FEATURE_COLS = [
    "city",
    "region_id",
    "week_of_year",
    "month",
    "year",
    "lag_1",
    "lag_2",
    "lag_4",
    "lag_8",
    "rolling_mean_4",
    "rolling_std_4",
    "rolling_mean_12",
]


def build_weekly_demand(daily: pd.DataFrame) -> pd.DataFrame:
    frame = daily.copy()
    frame["week_start"] = frame["ds"] - pd.to_timedelta(frame["ds"].dt.dayofweek, unit="D")
    weekly = (
        frame.groupby(["week_start", "city", "region_id"], as_index=False)["demand"]
        .sum()
        .rename(columns={"week_start": "ds"})
        .sort_values(["city", "region_id", "ds"])
    )
    return weekly


def make_weekly_panel(weekly_counts: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for (city, region_id), group in weekly_counts.groupby(["city", "region_id"]):
        group = group.sort_values("ds").set_index("ds")
        full_index = pd.date_range(group.index.min(), group.index.max(), freq="W-MON")
        group = group.reindex(full_index)
        group.index.name = "ds"
        group = group.assign(city=city, region_id=region_id)
        group["demand"] = group["demand"].fillna(0)
        parts.append(group.reset_index())

    panel = pd.concat(parts, ignore_index=True)
    panel["demand"] = panel["demand"].astype(float)
    return panel.sort_values(["city", "region_id", "ds"]).reset_index(drop=True)


def add_weekly_features(panel: pd.DataFrame) -> pd.DataFrame:
    enriched = panel.copy()
    enriched["week_of_year"] = enriched["ds"].dt.isocalendar().week.astype(int)
    enriched["month"] = enriched["ds"].dt.month
    enriched["year"] = enriched["ds"].dt.year

    enriched = enriched.sort_values(["city", "region_id", "ds"])
    grouped = enriched.groupby(["city", "region_id"], group_keys=False)

    for lag in (1, 2, 4, 8):
        enriched[f"lag_{lag}"] = grouped["demand"].transform(lambda s: s.shift(lag))

    enriched["rolling_mean_4"] = grouped["demand"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=1).mean()
    )
    enriched["rolling_std_4"] = grouped["demand"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=2).std()
    )
    enriched["rolling_mean_12"] = grouped["demand"].transform(
        lambda s: s.shift(1).rolling(12, min_periods=1).mean()
    )
    return enriched


def weekly_model_ready_frame(featured: pd.DataFrame) -> pd.DataFrame:
    required = ["lag_1", "lag_2", "lag_4", "lag_8", "rolling_mean_4", "rolling_mean_12"]
    return featured.dropna(subset=required).copy()


def split_weekly_holdout(
    model_data: pd.DataFrame, holdout_weeks: int = 2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff = model_data["ds"].max() - pd.Timedelta(weeks=holdout_weeks)
    train = model_data[model_data["ds"] <= cutoff].copy()
    test = model_data[model_data["ds"] > cutoff].copy()
    return train, test


def train_weekly_model(model_data: pd.DataFrame) -> Pipeline:
    model = build_model_pipeline(feature_cols=WEEKLY_FEATURE_COLS)
    model.fit(model_data[WEEKLY_FEATURE_COLS], model_data["demand"])
    return model


def evaluate_weekly_holdout(
    model: Pipeline, train: pd.DataFrame, test: pd.DataFrame
) -> dict[str, float]:
    model.fit(train[WEEKLY_FEATURE_COLS], train["demand"])
    pred = np.clip(model.predict(test[WEEKLY_FEATURE_COLS]), 0, None)
    y = test["demand"].values
    from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

    return {
        "mae": float(mean_absolute_error(y, pred)),
        "rmse": float(root_mean_squared_error(y, pred)),
        "mape": _safe_mape(y, pred),
        "r2": float(r2_score(y, pred)),
    }


def build_multistep_weekly_forecast(
    history_panel: pd.DataFrame,
    model_pipeline: Pipeline,
    n_weeks: int = 4,
) -> pd.DataFrame:
    forecast_rows: list[pd.DataFrame] = []
    extended = history_panel[["ds", "city", "region_id", "demand"]].copy()
    last_week = extended["ds"].max()

    for step in range(1, n_weeks + 1):
        forecast_week = last_week + pd.Timedelta(weeks=step)
        step_predictions: list[dict[str, Any]] = []

        for (city, region_id), group in extended.groupby(["city", "region_id"]):
            group = group.sort_values("ds")
            values = group["demand"].tolist()
            if not values:
                continue

            row = {
                "ds": forecast_week,
                "city": city,
                "region_id": region_id,
                "week_of_year": int(forecast_week.isocalendar().week),
                "month": forecast_week.month,
                "year": forecast_week.year,
                "lag_1": values[-1],
                "lag_2": values[-2] if len(values) >= 2 else values[-1],
                "lag_4": values[-4] if len(values) >= 4 else float(np.mean(values)),
                "lag_8": values[-8] if len(values) >= 8 else float(np.mean(values)),
                "rolling_mean_4": float(np.mean(values[-4:])),
                "rolling_std_4": float(np.std(values[-4:], ddof=1)) if len(values[-4:]) > 1 else 0.0,
                "rolling_mean_12": float(np.mean(values[-12:])),
            }
            step_predictions.append(row)

        step_df = pd.DataFrame(step_predictions)
        step_df["predicted_demand"] = np.clip(
            model_pipeline.predict(step_df[WEEKLY_FEATURE_COLS]), 0, None
        )
        forecast_rows.append(step_df[["ds", "city", "region_id", "predicted_demand"]])

        new_rows = step_df[["ds", "city", "region_id", "predicted_demand"]].rename(
            columns={"predicted_demand": "demand"}
        )
        extended = pd.concat([extended, new_rows], ignore_index=True)

    return pd.concat(forecast_rows, ignore_index=True)


def prepare_weekly_pipeline(dataset_kind: str = "delivery"):
    raw = load_city_data(dataset_kind)
    daily = build_daily_demand(raw)
    weekly = build_weekly_demand(daily)
    panel = make_weekly_panel(weekly)
    featured = add_weekly_features(panel)
    model_data = weekly_model_ready_frame(featured)
    return panel, model_data


def forecast_weekly_from_saved(
    history_panel: pd.DataFrame | None = None,
    *,
    dataset_kind: str = "delivery",
    n_weeks: int = 4,
) -> pd.DataFrame:
    model, _meta = load_artifact("weekly")
    if history_panel is None:
        history_panel, _ = prepare_weekly_pipeline(dataset_kind)
    return build_multistep_weekly_forecast(history_panel, model, n_weeks=n_weeks)
