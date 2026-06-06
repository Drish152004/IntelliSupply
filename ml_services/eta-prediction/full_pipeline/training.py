"""Model training module."""

from __future__ import annotations

import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def train_model(
    df: pd.DataFrame,
    stats: dict[str, pd.DataFrame],
    models_dir: Path = MODELS_DIR
) -> None:
    """Prepare features, split data, train LightGBM model, and save model artifacts."""
    print("Preparing training data...")
    
    # 1. Merge aoi_stats
    aoi_stats = stats["aoi_stats"]
    df = df.merge(aoi_stats[["aoi_id", "aoi_mean_eta", "aoi_count"]], on="aoi_id", how="left")
    
    # 2. Split train/test
    train = df[df["ds"] < 329].copy()
    test = df[df["ds"] >= 329].copy()
    
    # 3. Merge courier and load features
    courier_stats = stats["courier_stats"]
    courier_daily = stats["courier_daily"]
    courier_hourly = stats["courier_hourly"]

    for dataset in [train, test]:
        dataset["delivery_user_id"] = dataset["delivery_user_id"].astype(str)
        dataset["from_dipan_id"] = dataset["from_dipan_id"].astype(str)
        dataset["aoi_id"] = dataset["aoi_id"].astype(str)

    train = train.merge(
        courier_stats[["delivery_user_id", "courier_avg_eta", "courier_order_count"]],
        on="delivery_user_id",
        how="left",
    )
    test = test.merge(
        courier_stats[["delivery_user_id", "courier_avg_eta", "courier_order_count"]],
        on="delivery_user_id",
        how="left",
    )

    train = train.merge(courier_daily, on=["delivery_user_id", "ds"], how="left")
    test = test.merge(courier_daily, on=["delivery_user_id", "ds"], how="left")

    train = train.merge(courier_hourly, on=["delivery_user_id", "ds", "hour"], how="left")
    test = test.merge(courier_hourly, on=["delivery_user_id", "ds", "hour"], how="left")

    # Fill NaNs for load and courier statistics
    train[["courier_hourly_load", "courier_daily_load", "courier_avg_eta", "courier_order_count"]] = (
        train[["courier_hourly_load", "courier_daily_load", "courier_avg_eta", "courier_order_count"]]
        .fillna(0)
    )
    test[["courier_hourly_load", "courier_daily_load", "courier_avg_eta", "courier_order_count"]] = (
        test[["courier_hourly_load", "courier_daily_load", "courier_avg_eta", "courier_order_count"]]
        .fillna(0)
    )

    final_features = [
        "aoi_id",
        "delivery_user_id",
        "from_dipan_id",
        "hour",
        "weekday",
        "ds",
        "distance_km",
        "distance_hour_interaction",
        "courier_hourly_load",
        "courier_daily_load",
        "courier_avg_eta",
        "courier_order_count",
        "aoi_mean_eta",
        "aoi_count",
        "poi_lat",
        "poi_lng"
    ]

    X_train = train[final_features].copy()
    X_test = test[final_features].copy()

    y_train = train["eta_minutes"]
    y_test = test["eta_minutes"]

    # Align columns
    X_train, X_test = X_train.align(X_test, join='left', axis=1, fill_value=0)

    # Categorical features
    categorical_cols = ["aoi_id", "delivery_user_id", "from_dipan_id"]
    cat_mappings = {}
    for col in categorical_cols:
        if col in X_train.columns:
            X_train[col] = X_train[col].astype(str)
            X_test[col] = X_test[col].astype(str)
            
            X_train[col] = X_train[col].astype("category")
            cat_mappings[col] = X_train[col].cat.categories.tolist()

            X_test[col] = X_test[col].astype("category")
            X_test[col] = X_test[col].cat.set_categories(X_train[col].cat.categories)

            X_train[col] = X_train[col].cat.add_categories(["missing"]).fillna("missing")
            X_test[col] = X_test[col].cat.add_categories(["missing"]).fillna("missing")

    print(f"Training LightGBM model on {len(X_train)} samples...")
    model = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.03,
        num_leaves=64,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    # Evaluation
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    abs_err = np.abs(y_test - preds)

    print("\n--- Model Evaluation ---")
    print(f"MAE: {mae:.2f}")
    print(f"RMSE: {rmse:.2f}")
    print(f"R2: {r2:.3f}")
    print(f"P50 Error: {np.percentile(abs_err, 50):.2f}")
    print(f"P90 Error: {np.percentile(abs_err, 90):.2f}")
    print("------------------------\n")

    # Save artifacts
    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "lgbm_eta_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(models_dir / "features.pkl", "wb") as f:
        pickle.dump(final_features, f)
    with open(models_dir / "cat_mappings.pkl", "wb") as f:
        pickle.dump(cat_mappings, f)

    print("Model and features artifacts saved successfully!")
