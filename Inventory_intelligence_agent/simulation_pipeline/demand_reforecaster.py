from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from scenario_models import ScenarioPatch
from state_models import EventState, ForecastState, SimulationState

MODEL_PATH = (
    Path(__file__).parent.parent / "model" / "best_demand_forecasting_model.pkl"
)
DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_FORECAST_HORIZON = 30

_artifact: dict | None = None
_demand_analysis_df: pd.DataFrame | None = None


def patch_affects_forecast_drivers(patch: ScenarioPatch) -> bool:
    return bool(
        patch.event
        and (
            patch.event.promotion is not None
            or patch.event.seasonality is not None
            or patch.event.epidemic is not None
        )
    )


def reforecast_available() -> bool:
    try:
        import joblib  # noqa: F401
        import xgboost  # noqa: F401
    except ImportError:
        return False
    return MODEL_PATH.is_file()


def _load_artifact() -> dict:
    global _artifact
    if _artifact is not None:
        return _artifact

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Demand forecasting model not found at {MODEL_PATH}. "
            "Run data/Demand_Forecasting.ipynb to generate it."
        )

    import joblib

    _artifact = joblib.load(MODEL_PATH)
    return _artifact


def _get_demand_analysis_df() -> pd.DataFrame:
    global _demand_analysis_df
    if _demand_analysis_df is None:
        _demand_analysis_df = pd.read_csv(DATA_DIR / "demand_analysis_daily.csv")
    return _demand_analysis_df


def _hub_filter_value(hub_id: str, df: pd.DataFrame):
    if df["hub_id"].dtype.kind in "iu":
        try:
            return int(hub_id)
        except ValueError:
            pass
    return hub_id


def _latest_row(
    df: pd.DataFrame,
    date_col: str,
    simulation_date: str,
) -> pd.Series:
    eligible = df[df[date_col] <= simulation_date]
    if eligible.empty:
        raise ValueError(f"No rows found before {simulation_date}")
    return eligible.sort_values(date_col, ascending=False).iloc[0]


def _encode_seasonality(seasonality: str, label_encoders: dict) -> int:
    encoder = label_encoders["seasonality"]
    normalized = seasonality.strip().lower()
    for candidate in encoder.classes_:
        if str(candidate).strip().lower() == normalized:
            return int(encoder.transform([candidate])[0])
    raise ValueError(
        f"Unknown seasonality '{seasonality}'. "
        f"Expected one of: {list(encoder.classes_)}"
    )


def _encode_categorical(value, column: str, label_encoders: dict) -> int:
    encoder = label_encoders[column]
    return int(encoder.transform([str(value)])[0])


def _load_base_feature_row(
    base_state: SimulationState,
) -> tuple[pd.Series, float, float]:
    df = _get_demand_analysis_df()
    hub_key = _hub_filter_value(base_state.hub_id, df)

    product_rows = df[
        (df["hub_id"] == hub_key)
        & (df["product_id"] == base_state.product_id)
        & (df["category"] == base_state.category)
    ]
    if product_rows.empty:
        raise ValueError(
            f"No demand analysis rows for hub={base_state.hub_id}, "
            f"product={base_state.product_id}, category={base_state.category}"
        )

    base_row = _latest_row(
        product_rows,
        "demand_date",
        base_state.simulation_date,
    )

    sim_date = pd.Timestamp(base_state.simulation_date)
    lag_7_date = (sim_date - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    lag_7_rows = product_rows[product_rows["demand_date"] <= lag_7_date]
    if lag_7_rows.empty:
        lag_7_demand = 0.0
    else:
        lag_7_row = lag_7_rows.sort_values("demand_date", ascending=False).iloc[0]
        lag_7_demand = float(lag_7_row["actual_demand"])

    lag_1_demand = float(base_row["actual_demand"])
    return base_row, lag_1_demand, lag_7_demand


def _build_future_rows(
    base_state: SimulationState,
    event: EventState,
    base_row: pd.Series,
    lag_1_demand: float,
    lag_7_demand: float,
    horizon: int,
    label_encoders: dict,
) -> pd.DataFrame:
    sim_date = pd.Timestamp(base_state.simulation_date)
    hub_key = _hub_filter_value(base_state.hub_id, _get_demand_analysis_df())

    promotion = int(event.promotion)
    epidemic = int(event.epidemic)
    seasonality_encoded = _encode_seasonality(event.seasonality, label_encoders)

    product_id_encoded = _encode_categorical(
        base_state.product_id,
        "product_id",
        label_encoders,
    )
    category_encoded = _encode_categorical(
        base_state.category,
        "category",
        label_encoders,
    )
    weather_encoded = _encode_categorical(
        base_row["weather_condition"],
        "weather_condition",
        label_encoders,
    )

    rolling_7 = float(base_row["rolling_7_avg_demand"])
    rolling_30 = float(base_row["rolling_30_avg_demand"])
    rolling_7_std = float(base_row["rolling_7_std_demand"])
    rolling_30_std = float(base_row["rolling_30_std_demand"])

    future_rows: list[dict] = []
    for horizon_day in range(1, horizon + 1):
        forecast_date = sim_date + pd.Timedelta(days=horizon_day)
        future_rows.append(
            {
                "forecast_date": forecast_date,
                "hub_id": hub_key,
                "product_id": product_id_encoded,
                "category": category_encoded,
                "price": float(base_row["price"]),
                "discount": float(base_row["discount"]),
                "promotion": promotion,
                "competitor_pricing": float(base_row["competitor_pricing"]),
                "weather_condition": weather_encoded,
                "seasonality": seasonality_encoded,
                "epidemic": epidemic,
                "year": forecast_date.year,
                "month": forecast_date.month,
                "day": forecast_date.day,
                "day_of_week": forecast_date.dayofweek,
                "is_weekend": int(forecast_date.dayofweek in (5, 6)),
                "lag_1_demand": lag_1_demand,
                "lag_7_demand": lag_7_demand,
                "rolling_7_avg_demand": rolling_7,
                "rolling_30_avg_demand": rolling_30,
                "rolling_7_std_demand": rolling_7_std,
                "rolling_30_std_demand": rolling_30_std,
                "forecast_horizon_day": horizon_day,
            }
        )

    return pd.DataFrame(future_rows)


def _confidence_score(predicted_df: pd.DataFrame) -> pd.Series:
    scores = np.where(
        predicted_df["rolling_30_avg_demand"] <= 0,
        70,
        100
        - (
            predicted_df["rolling_30_std_demand"]
            / predicted_df["rolling_30_avg_demand"]
            * 100
        ),
    )
    return pd.Series(scores).clip(lower=50, upper=95).round(2)


def reforecast_demand(
    base_state: SimulationState,
    event: EventState,
    base_forecast: ForecastState,
    horizon: int,
) -> ForecastState:
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if horizon > DEFAULT_FORECAST_HORIZON:
        raise ValueError(
            f"Planning window {horizon} exceeds model forecast "
            f"horizon ({DEFAULT_FORECAST_HORIZON} days)."
        )

    artifact = _load_artifact()
    model = artifact["model"]
    feature_cols = artifact["feature_cols"]
    label_encoders = artifact["label_encoders"]

    base_row, lag_1_demand, lag_7_demand = _load_base_feature_row(base_state)
    future_df = _build_future_rows(
        base_state,
        event,
        base_row,
        lag_1_demand,
        lag_7_demand,
        horizon,
        label_encoders,
    )

    predictions = model.predict(future_df[feature_cols])
    future_df["predicted_demand"] = (
        pd.Series(predictions).clip(lower=0).round().astype(int)
    )
    future_df["lower_bound"] = (
        future_df["predicted_demand"] - future_df["rolling_30_std_demand"]
    ).clip(lower=0).round().astype(int)
    future_df["upper_bound"] = (
        future_df["predicted_demand"] + future_df["rolling_30_std_demand"]
    ).round().astype(int)
    future_df["confidence_score"] = _confidence_score(future_df)

    day_one = future_df.iloc[0]
    forecast_daily = future_df["predicted_demand"].astype(float).tolist()
    lower_bound = float(day_one["lower_bound"])
    upper_bound = float(day_one["upper_bound"])

    return replace(
        base_forecast,
        forecast_date=str(day_one["forecast_date"].date()),
        predicted_demand=float(day_one["predicted_demand"]),
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        forecast_uncertainty=upper_bound - lower_bound,
        confidence_score=float(day_one["confidence_score"]),
        forecast_daily=forecast_daily,
    )
