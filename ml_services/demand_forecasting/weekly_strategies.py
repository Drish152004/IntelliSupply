"""
Improved weekly forecasts:
  1) daily_sum — multistep daily model, aggregate to calendar weeks
  2) hierarchical — city-week totals (from daily sum) split by historical region shares
  3) native — original per-region weekly model (baseline)
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline

from .lade_demand import (
    FEATURE_COLS,
    _safe_mape,
    add_features,
    build_daily_demand,
    build_model_pipeline,
    build_multistep_forecast,
    load_city_data,
    make_daily_panel,
    model_ready_frame,
    train_final_model,
)
from .lade_weekly import (
    WEEKLY_FEATURE_COLS,
    add_weekly_features,
    build_multistep_weekly_forecast,
    build_weekly_demand,
    make_weekly_panel,
    prepare_weekly_pipeline,
    weekly_model_ready_frame,
)

WeeklyStrategy = Literal["daily_sum", "hierarchical", "native"]

CITY_WEEKLY_FEATURE_COLS = [
    "city",
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


def to_week_start(ds: pd.Series) -> pd.Series:
    return ds - pd.to_timedelta(ds.dt.dayofweek, unit="D")


def aggregate_daily_forecast_to_weekly(daily_forecast: pd.DataFrame) -> pd.DataFrame:
    frame = daily_forecast.copy()
    frame["ds"] = to_week_start(frame["ds"])
    weekly = (
        frame.groupby(["ds", "city", "region_id"], as_index=False)["predicted_demand"]
        .sum()
        .sort_values(["city", "region_id", "ds"])
    )
    return weekly


def compute_region_shares(
    weekly_panel: pd.DataFrame,
    *,
    lookback_weeks: int = 8,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Historical fraction of city weekly demand per region (sums to 1 per city-week)."""
    panel = weekly_panel.copy()
    if as_of is not None:
        panel = panel[panel["ds"] <= as_of]

    last_week = panel["ds"].max()
    cutoff = last_week - pd.Timedelta(weeks=lookback_weeks)
    recent = panel[panel["ds"] > cutoff]

    city_totals = recent.groupby(["ds", "city"], as_index=False)["demand"].sum().rename(
        columns={"demand": "city_total"}
    )
    merged = recent.merge(city_totals, on=["ds", "city"], how="left")
    merged["share"] = np.where(merged["city_total"] > 0, merged["demand"] / merged["city_total"], 0.0)

    shares = (
        merged.groupby(["city", "region_id"], as_index=False)["share"]
        .mean()
        .rename(columns={"share": "region_share"})
    )

    # Renormalize per city
    city_sum = shares.groupby("city")["region_share"].transform("sum")
    shares["region_share"] = np.where(city_sum > 0, shares["region_share"] / city_sum, 0.0)
    return shares


def split_city_weekly_to_regions(
    city_weekly: pd.DataFrame,
    shares: pd.DataFrame,
) -> pd.DataFrame:
    """city_weekly: columns ds, city, predicted_demand (city total)."""
    merged = city_weekly.merge(shares, on="city", how="left")
    merged["predicted_demand"] = merged["predicted_demand"] * merged["region_share"]
    return merged[["ds", "city", "region_id", "predicted_demand"]].sort_values(
        ["ds", "city", "region_id"]
    )


def make_city_weekly_panel(weekly_panel: pd.DataFrame) -> pd.DataFrame:
    city = (
        weekly_panel.groupby(["ds", "city"], as_index=False)["demand"]
        .sum()
        .sort_values(["city", "ds"])
    )
    parts = []
    for city_name, group in city.groupby("city"):
        group = group.sort_values("ds").set_index("ds")
        full_index = pd.date_range(group.index.min(), group.index.max(), freq="W-MON")
        group = group.reindex(full_index)
        group.index.name = "ds"
        group = group.assign(city=city_name)
        group["demand"] = group["demand"].fillna(0)
        parts.append(group.reset_index())
    return pd.concat(parts, ignore_index=True)


def add_city_weekly_features(panel: pd.DataFrame) -> pd.DataFrame:
    enriched = panel.copy()
    enriched["week_of_year"] = enriched["ds"].dt.isocalendar().week.astype(int)
    enriched["month"] = enriched["ds"].dt.month
    enriched["year"] = enriched["ds"].dt.year
    enriched = enriched.sort_values(["city", "ds"])
    grouped = enriched.groupby("city", group_keys=False)

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


def build_city_multistep_forecast(
    city_panel: pd.DataFrame,
    model: Pipeline,
    n_weeks: int,
) -> pd.DataFrame:
    extended = city_panel[["ds", "city", "demand"]].copy()
    last_week = extended["ds"].max()
    rows: list[dict] = []

    for step in range(1, n_weeks + 1):
        forecast_week = last_week + pd.Timedelta(weeks=step)
        step_rows = []
        for city, group in extended.groupby("city"):
            group = group.sort_values("ds")
            values = group["demand"].tolist()
            if not values:
                continue
            step_rows.append(
                {
                    "ds": forecast_week,
                    "city": city,
                    "week_of_year": int(forecast_week.isocalendar().week),
                    "month": forecast_week.month,
                    "year": forecast_week.year,
                    "lag_1": values[-1],
                    "lag_2": values[-2] if len(values) >= 2 else values[-1],
                    "lag_4": values[-4] if len(values) >= 4 else float(np.mean(values)),
                    "lag_8": values[-8] if len(values) >= 8 else float(np.mean(values)),
                    "rolling_mean_4": float(np.mean(values[-4:])),
                    "rolling_std_4": float(np.std(values[-4:], ddof=1))
                    if len(values[-4:]) > 1
                    else 0.0,
                    "rolling_mean_12": float(np.mean(values[-12:])),
                }
            )
        step_df = pd.DataFrame(step_rows)
        step_df["predicted_demand"] = np.clip(
            model.predict(step_df[CITY_WEEKLY_FEATURE_COLS]), 0, None
        )
        rows.append(step_df[["ds", "city", "predicted_demand"]])
        new_hist = step_df.rename(columns={"predicted_demand": "demand"})[["ds", "city", "demand"]]
        extended = pd.concat([extended, new_hist], ignore_index=True)

    return pd.concat(rows, ignore_index=True)


def forecast_weekly_daily_sum(
    daily_panel: pd.DataFrame,
    daily_model: Pipeline,
    n_weeks: int,
) -> pd.DataFrame:
    daily_fc = build_multistep_forecast(daily_panel, daily_model, n_days=n_weeks * 7)
    return aggregate_daily_forecast_to_weekly(daily_fc)


def forecast_weekly_hierarchical(
    daily_panel: pd.DataFrame,
    weekly_panel: pd.DataFrame,
    daily_model: Pipeline,
    n_weeks: int,
    *,
    lookback_weeks: int = 8,
) -> pd.DataFrame:
    daily_fc = build_multistep_forecast(daily_panel, daily_model, n_days=n_weeks * 7)
    region_weekly = aggregate_daily_forecast_to_weekly(daily_fc)
    city_weekly = (
        region_weekly.groupby(["ds", "city"], as_index=False)["predicted_demand"]
        .sum()
    )
    shares = compute_region_shares(weekly_panel, lookback_weeks=lookback_weeks)
    return split_city_weekly_to_regions(city_weekly, shares)


def forecast_weekly_hierarchical_city_model(
    weekly_panel: pd.DataFrame,
    city_model: Pipeline,
    n_weeks: int,
    *,
    lookback_weeks: int = 8,
) -> pd.DataFrame:
    city_panel = make_city_weekly_panel(weekly_panel)
    city_fc = build_city_multistep_forecast(city_panel, city_model, n_weeks=n_weeks)
    shares = compute_region_shares(weekly_panel, lookback_weeks=lookback_weeks)
    return split_city_weekly_to_regions(city_fc, shares)


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        "mape": _safe_mape(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate_predictions(actual: pd.DataFrame, predicted: pd.DataFrame) -> dict[str, float]:
    merged = actual.merge(
        predicted,
        on=["ds", "city", "region_id"],
        how="inner",
        suffixes=("_actual", "_pred"),
    )
    if merged.empty:
        return {"mae": float("nan"), "rmse": float("nan"), "mape": float("nan"), "r2": float("nan")}
    y = merged["demand"].values
    p = np.clip(merged["predicted_demand"].values, 0, None)
    return metrics_dict(y, p)


def backtest_weekly_strategies(
    dataset_kind: str = "delivery",
    holdout_weeks: int = 2,
) -> dict[str, dict]:
    """
    Train on history before holdout; score on held-out region-weeks.
    Returns metrics per strategy + recommended strategy name.
    """
    raw = load_city_data(dataset_kind)
    daily = build_daily_demand(raw)
    daily_panel = make_daily_panel(daily)
    weekly = build_weekly_demand(daily)
    weekly_panel = make_weekly_panel(weekly)

    cutoff = weekly_panel["ds"].max() - pd.Timedelta(weeks=holdout_weeks)
    cutoff_day = cutoff + pd.Timedelta(days=6)

    actual = weekly_panel[weekly_panel["ds"] > cutoff][["ds", "city", "region_id", "demand"]]

    daily_train_panel = daily_panel[daily_panel["ds"] <= cutoff_day]
    daily_train_data = model_ready_frame(add_features(daily_train_panel))
    daily_model = train_final_model(daily_train_data)

    weekly_train_panel = weekly_panel[weekly_panel["ds"] <= cutoff]
    native_featured = add_weekly_features(weekly_train_panel)
    native_train = weekly_model_ready_frame(native_featured)
    native_model = build_model_pipeline(feature_cols=WEEKLY_FEATURE_COLS)
    native_model.fit(native_train[WEEKLY_FEATURE_COLS], native_train["demand"])

    city_panel = make_city_weekly_panel(weekly_train_panel)
    city_featured = add_city_weekly_features(city_panel)
    city_train = city_featured.dropna(
        subset=["lag_1", "lag_2", "lag_4", "lag_8", "rolling_mean_4", "rolling_mean_12"]
    )
    city_model = build_model_pipeline(feature_cols=CITY_WEEKLY_FEATURE_COLS)
    city_model.fit(city_train[CITY_WEEKLY_FEATURE_COLS], city_train["demand"])

    hist_daily = daily_panel[daily_panel["ds"] <= cutoff_day]
    hist_weekly = weekly_train_panel

    results: dict[str, dict] = {}

    native_fc = build_multistep_weekly_forecast(hist_weekly, native_model, n_weeks=holdout_weeks)
    results["native"] = evaluate_predictions(actual, native_fc)

    daily_sum_fc = forecast_weekly_daily_sum(hist_daily, daily_model, holdout_weeks)
    results["daily_sum"] = evaluate_predictions(actual, daily_sum_fc)

    hier_fc = forecast_weekly_hierarchical(
        hist_daily, hist_weekly, daily_model, holdout_weeks
    )
    results["hierarchical"] = evaluate_predictions(actual, hier_fc)

    hier_city_fc = forecast_weekly_hierarchical_city_model(
        hist_weekly, city_model, holdout_weeks
    )
    results["hierarchical_city_model"] = evaluate_predictions(actual, hier_city_fc)

    best = max(
        results,
        key=lambda k: (results[k].get("r2") or -1, -(results[k].get("mae") or 1e18)),
    )
    results["_recommended"] = best
    return results


def produce_weekly_forecast(
    strategy: WeeklyStrategy,
    *,
    dataset_kind: str = "delivery",
    n_weeks: int = 4,
    daily_panel: pd.DataFrame | None = None,
    weekly_panel: pd.DataFrame | None = None,
    daily_model: Pipeline | None = None,
    weekly_model: Pipeline | None = None,
) -> pd.DataFrame:
    """Production forecast using the chosen strategy (models trained on full history)."""
    from .lade_demand import load_artifact

    if daily_panel is None or weekly_panel is None:
        wp, _ = prepare_weekly_pipeline(dataset_kind)
        weekly_panel = wp
        raw = load_city_data(dataset_kind)
        daily_panel = make_daily_panel(build_daily_demand(raw))

    if strategy == "native":
        if weekly_model is None:
            weekly_model, _ = load_artifact("weekly")
        return build_multistep_weekly_forecast(weekly_panel, weekly_model, n_weeks=n_weeks)

    if daily_model is None:
        daily_model, _ = load_artifact("daily")

    if strategy == "daily_sum":
        return forecast_weekly_daily_sum(daily_panel, daily_model, n_weeks)

    if strategy == "hierarchical":
        return forecast_weekly_hierarchical(daily_panel, weekly_panel, daily_model, n_weeks)

    raise ValueError(f"Unknown strategy: {strategy}")
