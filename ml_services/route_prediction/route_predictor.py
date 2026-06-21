"""Route ranking inference (v3) — shared by notebook, FastAPI, and agents."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

MINUTES_PER_STOP_EST = 8.0


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["receipt_time"] = pd.to_datetime(out["receipt_time"])
    out["hour_of_day"] = out["receipt_time"].dt.hour
    out["minute"] = out["receipt_time"].dt.minute
    out["is_morning"] = (out["hour_of_day"] < 12).astype(np.int8)
    out["is_afternoon"] = (
        (out["hour_of_day"] >= 12) & (out["hour_of_day"] < 17)
    ).astype(np.int8)
    out["is_evening"] = (out["hour_of_day"] >= 17).astype(np.int8)
    return out


def apply_encoders(frame: pd.DataFrame, encoders, aoi_map: dict) -> pd.DataFrame:
    out = frame.copy()
    for col, le in encoders.items():
        known = set(le.classes_)
        out[col + "_enc"] = out[col].astype(str).map(
            lambda x, le=le, known=known: int(le.transform([x])[0]) if x in known else -1
        )
    out["aoi_id_enc"] = out["aoi_id"].astype(str).map(aoi_map).fillna(-1).astype(np.int32)
    return out


def simulated_elapsed_minutes(step: int) -> float:
    return step * MINUTES_PER_STOP_EST


def augment_candidate_features(
    candidates: pd.DataFrame,
    cur_lat: float,
    cur_lng: float,
    step: int,
    route_start_time: pd.Timestamp,
) -> pd.DataFrame:
    out = candidates.copy()
    dlat = out["poi_lat"].values - cur_lat
    dlng = out["poi_lng"].values - cur_lng
    dist = np.hypot(dlat, dlng)
    elapsed = simulated_elapsed_minutes(step)
    simulated_now = route_start_time + pd.Timedelta(minutes=elapsed)
    rt = pd.to_datetime(out["receipt_time"])

    out["dist_to_candidate"] = dist
    out["log_dist_to_candidate"] = np.log1p(dist)
    out["stops_completed"] = step
    out["stops_remaining"] = len(out)
    out["elapsed_minutes"] = elapsed
    out["receipt_hour"] = rt.dt.hour
    wait = (simulated_now - rt).dt.total_seconds() / 60
    out["wait_since_receipt_min"] = np.clip(wait, 0, None)
    out["log_wait_since_receipt"] = np.log1p(out["wait_since_receipt_min"])
    bearing = np.arctan2(dlng, dlat)
    out["bearing_sin"] = np.sin(bearing)
    out["bearing_cos"] = np.cos(bearing)
    return out


class _RoutePredictorUnpickler(pickle.Unpickler):
    """Load pickles saved from the notebook (__main__.RoutePredictor)."""

    def find_class(self, module, name):
        if name == "RoutePredictor":
            return RoutePredictor
        return super().find_class(module, name)


class RoutePredictor:
    """LightGBM ranker + encoders + greedy route decode (v3)."""

    def __init__(
        self,
        model,
        feature_cols,
        label_encoders,
        aoi_map,
        version: str = "3.0",
        minutes_per_stop_est: float = MINUTES_PER_STOP_EST,
    ):
        self.model = model
        self.feature_cols = list(feature_cols)
        self.label_encoders = label_encoders
        self.aoi_map = aoi_map
        self.version = version
        self.minutes_per_stop_est = minutes_per_stop_est

    def _prepare_orders(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        out = add_time_features(orders_df.copy())
        return apply_encoders(out, self.label_encoders, self.aoi_map)

    def _score_candidates(
        self,
        current_lat: float,
        current_lng: float,
        remaining: pd.DataFrame,
        step: int,
        route_start_time: pd.Timestamp,
    ):
        feat = augment_candidate_features(
            remaining, current_lat, current_lng, step, route_start_time
        )
        X = feat[self.feature_cols].values
        scores = self.model.predict(X)
        best_idx = int(np.argmax(scores))
        return feat.iloc[best_idx], scores, feat["order_id"].tolist()

    def predict_next_stop(
        self,
        current_lat: float,
        current_lng: float,
        remaining_orders_df: pd.DataFrame,
        stops_completed: int,
        route_start_time: pd.Timestamp,
    ):
        remaining = self._prepare_orders(remaining_orders_df).reset_index(drop=True)
        row, scores, order_ids = self._score_candidates(
            current_lat, current_lng, remaining, stops_completed, route_start_time
        )
        score_map = {oid: float(s) for oid, s in zip(order_ids, scores)}
        return row["order_id"], score_map, row

    def predict_full_sequence(self, route_orders_df: pd.DataFrame) -> list[str]:
        remaining = self._prepare_orders(route_orders_df).reset_index(drop=True)
        sequence = []
        cur_lat = float(remaining.iloc[0]["receipt_lat"])
        cur_lng = float(remaining.iloc[0]["receipt_lng"])
        route_start_time = pd.Timestamp(remaining.iloc[0]["receipt_time"])

        for step in range(len(remaining)):
            oid, _, chosen = self.predict_next_stop(
                cur_lat, cur_lng, remaining, step, route_start_time
            )
            sequence.append(str(oid))
            cur_lat, cur_lng = float(chosen["poi_lat"]), float(chosen["poi_lng"])
            remaining = remaining[remaining["order_id"] != oid].reset_index(drop=True)

        return sequence

    def save(self, path: str | Path) -> None:
        path = Path(path)
        with path.open("wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path: str | Path) -> RoutePredictor:
        path = Path(path)
        with path.open("rb") as f:
            obj = _RoutePredictorUnpickler(f).load()
        if not isinstance(obj, cls):
            raise TypeError(f"Expected {cls}, got {type(obj)}")
        return obj
