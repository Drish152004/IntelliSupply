import numpy as np


def add_time_features(df):
    df["hour_of_day"] = df["receipt_time"].dt.hour
    df["minute"] = df["receipt_time"].dt.minute
    df["day_of_week"] = df["receipt_time"].dt.dayofweek
    df["month"] = df["receipt_time"].dt.month

    df["is_morning"] = (df["hour_of_day"] < 12).astype(np.int8)
    df["is_afternoon"] = ((df["hour_of_day"] >= 12) & (df["hour_of_day"] < 17)).astype(np.int8)
    df["is_evening"] = (df["hour_of_day"] >= 17).astype(np.int8)

    return df


def add_distance_features(df):
    dlat = df["poi_lat"] - df["receipt_lat"]
    dlng = df["poi_lng"] - df["receipt_lng"]

    df["euclidean_dist"] = np.sqrt(dlat**2 + dlng**2)
    df["manhattan_dist"] = np.abs(dlat) + np.abs(dlng)
    df["log_distance"] = np.log1p(df["euclidean_dist"])

    bearing = np.arctan2(dlng, dlat)
    df["bearing_sin"] = np.sin(bearing)
    df["bearing_cos"] = np.cos(bearing)

    return df


def add_route_features(df):
    df = df.sort_values(["delivery_user_id", "ds", "sign_time"])

    df["stop_rank"] = df.groupby(["delivery_user_id", "ds"]).cumcount()
    df["total_stops"] = df.groupby(["delivery_user_id", "ds"])["stop_rank"].transform("max") + 1
    df["stops_remaining"] = df["total_stops"] - df["stop_rank"]

    return df


def add_wait_features(df):
    group_min = df.groupby(["delivery_user_id", "ds"])["receipt_time"].transform("min")

    df["wait_since_first_order_min"] = (
        (df["receipt_time"] - group_min).dt.total_seconds() / 60.0
    ).clip(lower=0)

    df["log_wait_since_first_order"] = np.log1p(df["wait_since_first_order_min"])

    df["receipt_hour"] = df["receipt_time"].dt.hour

    return df
