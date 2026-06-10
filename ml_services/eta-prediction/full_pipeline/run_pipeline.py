from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from full_pipeline.preprocess import load_and_clean
from full_pipeline.feature_engineering import *
from full_pipeline.training import *
from full_pipeline.inference import ETAPredictor


# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_DIR / "data/Delivery.csv"
MODEL_PATH = BASE_DIR / "models/eta_lightgbm_model.pkl"

TEST_RATIO = 0.2


# =============================================================================
# MODEL PARAMS
# =============================================================================

LGB_PARAMS = {
    "objective": "regression",
    "metric": "l1",
    "boosting_type": "gbdt",
    "learning_rate": 0.03,
    "num_leaves": 255,
    "max_depth": -1,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 5,
    "lambda_l1": 1.0,
    "lambda_l2": 1.0,
    "max_bin": 255,
    "verbosity": -1,
    "seed": 42,
}


# =============================================================================
# FEATURES
# =============================================================================

FEATURE_COLS = [
    "poi_lat","poi_lng","receipt_lat","receipt_lng",
    "euclidean_dist","manhattan_dist","log_distance",
    "bearing_sin","bearing_cos",
    "hour_of_day","minute","day_of_week","month",
    "is_morning","is_afternoon","is_evening",
    "stop_rank","stops_remaining",
    "receipt_hour",
    "wait_since_first_order_min","log_wait_since_first_order",
    "city_name_enc","typecode_enc","aoi_id_enc",
    "city_avg_eta","type_avg_eta","aoi_avg_eta",
    "courier_avg_eta","courier_total_orders",
]


# =============================================================================
# FULL EVALUATION
# =============================================================================

def full_evaluation(train_df, test_df, preds, model):

    TARGET_COL = "actual_eta_min"
    y_test = test_df[TARGET_COL]

    # =============================
    # BASIC METRICS
    # =============================
    print("\n==============================")
    print("ETA METRICS")
    print("==============================")

    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mape = np.mean(np.abs((y_test - preds) / y_test)) * 100

    within_10 = np.mean(np.abs(y_test - preds) <= 10) * 100
    within_20 = np.mean(np.abs(y_test - preds) <= 20) * 100
    within_30 = np.mean(np.abs(y_test - preds) <= 30) * 100

    print(f"MAE  : {mae:.2f} minutes")
    print(f"RMSE : {rmse:.2f} minutes")
    print(f"MAPE : {mape:.2f}%")

    print()
    print(f"Within 10 min : {within_10:.2f}%")
    print(f"Within 20 min : {within_20:.2f}%")
    print(f"Within 30 min : {within_30:.2f}%")

    # =============================
    # ROUTE LEVEL
    # =============================
    route_eval = test_df.copy()
    route_eval["pred_eta"] = preds

    route_group = (
        route_eval.groupby(["delivery_user_id", "ds"])
        .agg(
            actual_route_eta=(TARGET_COL, "mean"),
            predicted_route_eta=("pred_eta", "mean"),
            total_orders=("order_id", "count"),
        )
        .reset_index()
    )

    route_group["route_abs_error"] = np.abs(
        route_group["actual_route_eta"]
        - route_group["predicted_route_eta"]
    )

    route_mae = route_group["route_abs_error"].mean()

    print(f"\nRoute-level MAE: {route_mae:.2f} minutes")

    # =============================
    # FINAL SUMMARY
    # =============================
    print("\n==============================")
    print("FINAL SUMMARY")
    print("==============================")

    print(f"Train rows          : {len(train_df):,}")
    print(f"Test rows           : {len(test_df):,}")
    print(f"Features            : {len(FEATURE_COLS)}")
    print(f"Best iteration      : {model.best_iteration}")
    print(f"Final MAE           : {mae:.2f} min")
    print(f"Final RMSE          : {rmse:.2f} min")
    print(f"Final MAPE          : {mape:.2f}%")
    print(f"Route-level MAE     : {route_mae:.2f} min")

    # =============================
    # ADVANCED ANALYSIS
    # =============================
    print("\n==============================")
    print("DETAILED BUCKETED ANALYSIS")
    print("==============================")

    analysis_df = test_df.copy()
    analysis_df["pred_eta"] = preds
    analysis_df["abs_error"] = np.abs(analysis_df[TARGET_COL] - analysis_df["pred_eta"])
    analysis_df["ape"] = analysis_df["abs_error"] / analysis_df[TARGET_COL] * 100

    # -----------------------------
    # ETA BUCKETS
    # -----------------------------
    analysis_df["eta_bucket"] = pd.cut(
        analysis_df[TARGET_COL],
        bins=[0, 100, 200, 300],
        labels=["0-100", "100-200", "200-300"]
    )

    print("\n--- ETA BUCKET PERFORMANCE ---")
    print(analysis_df.groupby("eta_bucket").agg(
        count=("abs_error", "count"),
        mae=("abs_error", "mean"),
        rmse=("abs_error", lambda x: np.sqrt(np.mean(x**2))),
        mape=("ape", "mean"),
    ).reset_index())

    # -----------------------------
    # DISTANCE BUCKETS
    # -----------------------------
    analysis_df["dist_bucket"] = pd.cut(
        analysis_df["euclidean_dist"],
        bins=[0, 0.01, 0.03, 0.05, 0.1, 0.2, 1.0],
        labels=["very_short", "short", "mid", "long", "very_long", "extreme"]
    )

    print("\n--- DISTANCE BUCKET PERFORMANCE ---")
    print(analysis_df.groupby("dist_bucket").agg(
        count=("abs_error", "count"),
        mae=("abs_error", "mean"),
        mape=("ape", "mean"),
    ).reset_index())

    # -----------------------------
    # TIME OF DAY
    # -----------------------------
    analysis_df["time_bucket"] = pd.cut(
        analysis_df["hour_of_day"],
        bins=[0, 6, 11, 16, 20, 24],
        labels=["night", "morning", "afternoon", "evening", "late_night"]
    )

    print("\n--- TIME OF DAY PERFORMANCE ---")
    print(analysis_df.groupby("time_bucket").agg(
        count=("abs_error", "count"),
        mae=("abs_error", "mean"),
        mape=("ape", "mean"),
    ).reset_index())

    # -----------------------------
    # ROUTE SIZE
    # -----------------------------
    route_counts = test_df.groupby(["delivery_user_id", "ds"]).size().reset_index(name="route_size")
    analysis_df = analysis_df.merge(route_counts, on=["delivery_user_id", "ds"], how="left")

    analysis_df["route_size_bucket"] = pd.cut(
        analysis_df["route_size"],
        bins=[0, 1, 3, 5, 10, 50, 1000],
        labels=["1", "2-3", "4-5", "6-10", "10-50", "50+"]
    )

    print("\n--- ROUTE SIZE PERFORMANCE ---")
    print(analysis_df.groupby("route_size_bucket").agg(
        count=("abs_error", "count"),
        mae=("abs_error", "mean"),
        mape=("ape", "mean"),
    ).reset_index())

    # -----------------------------
    # WORST ROUTES
    # -----------------------------
    print("\n--- WORST ROUTES (TOP 10) ---")
    worst_routes = analysis_df.groupby(["delivery_user_id", "ds"]).agg(
        mae=("abs_error", "mean"),
        count=("abs_error", "count")
    ).reset_index().sort_values("mae", ascending=False)

    print(worst_routes.head(10))

    # -----------------------------
    # MAPE STABILITY
    # -----------------------------
    print("\n==============================")
    print("MAPE STABILITY CHECK")
    print("==============================")

    short_trips = analysis_df[analysis_df[TARGET_COL] <= 15]
    long_trips = analysis_df[analysis_df[TARGET_COL] > 60]

    def safe_mape(df):
        return np.mean(
            np.abs(df[TARGET_COL] - df["pred_eta"]) /
            np.maximum(df[TARGET_COL], 1)
        ) * 100

    print(f"Short trips MAPE (<=15 min): {safe_mape(short_trips):.2f}%")
    print(f"Long trips MAPE (>60 min)  : {safe_mape(long_trips):.2f}%")

    # -----------------------------
    # ERROR DISTRIBUTION
    # -----------------------------
    print("\n==============================")
    print("ERROR DISTRIBUTION")
    print("==============================")

    print("P50 AE :", np.percentile(analysis_df["abs_error"], 50))
    print("P90 AE :", np.percentile(analysis_df["abs_error"], 90))
    print("P95 AE :", np.percentile(analysis_df["abs_error"], 95))
    print("P99 AE :", np.percentile(analysis_df["abs_error"], 99))


# =============================================================================
# MAIN RUN
# =============================================================================

def run():

    print("\n==============================")
    print("LOADING DATA")
    print("==============================")

    df = load_and_clean(DATA_PATH)

    df = add_time_features(df)
    df = add_distance_features(df)
    df = add_route_features(df)
    df = add_wait_features(df)

    df, city_eta, type_eta, aoi_eta, courier_avg, courier_orders = build_aggregates(df)
    df, encoders, aoi_map = encode(df)

    # =============================
    # SPLIT
    # =============================
    sorted_ds = sorted(df["ds"].unique())
    cutoff = sorted_ds[int(len(sorted_ds) * (1 - TEST_RATIO))]

    train_df = df[df["ds"] < cutoff]
    test_df = df[df["ds"] >= cutoff]

    print(f"Train rows: {len(train_df):,}")
    print(f"Test rows : {len(test_df):,}")

    # =============================
    # TRAIN
    # =============================
    X_train = train_df[FEATURE_COLS]
    y_train = train_df["actual_eta_min"]

    X_test = test_df[FEATURE_COLS]
    y_test = test_df["actual_eta_min"]

    print("\n==============================")
    print("TRAINING MODEL")
    print("==============================")

    model = train_model(
        X_train,
        y_train,
        X_test,
        y_test,
        LGB_PARAMS,
        FEATURE_COLS,
        num_round=1200,
        early_stop=100,
    )

    # =============================
    # PREDICTION
    # =============================
    preds = model.predict(X_test, num_iteration=model.best_iteration)
    preds = np.clip(preds, 1, 480)

    # ✅ FULL EVALUATION
    full_evaluation(train_df, test_df, preds, model)

    # =============================
    # SAVE MODEL
    # =============================
    predictor = ETAPredictor(
        model,
        FEATURE_COLS,
        encoders,
        aoi_map,
        city_eta,
        type_eta,
        aoi_eta,
        courier_avg,
        courier_orders,
    )

    predictor.save(MODEL_PATH)

    print("\n✅ MODEL SAVED AT:", MODEL_PATH)


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    run()
