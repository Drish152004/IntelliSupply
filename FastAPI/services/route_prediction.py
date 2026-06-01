"""Route prediction inference helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from services.registry import _ensure_route_path, get_route_predictor


def predict_next_stop(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_route_path()
    from route_predictor import orders_to_dataframe

    pred = get_route_predictor()
    remaining = orders_to_dataframe([o for o in payload["remaining_orders"]])
    route_start = pd.to_datetime(payload["route_start_time"])
    order_id, score_map, row = pred.predict_next_stop(
        payload["current_lat"],
        payload["current_lng"],
        remaining,
        payload.get("stops_completed", 0),
        route_start,
    )
    return {
        "order_id": str(order_id),
        "candidate_scores": [
            {"order_id": oid, "score": float(score)} for oid, score in score_map.items()
        ],
        "chosen": {
            "order_id": str(order_id),
            "poi_lat": float(row["poi_lat"]),
            "poi_lng": float(row["poi_lng"]),
            "dist_to_candidate": float(row.get("dist_to_candidate", 0)),
            "stops_remaining": int(row.get("stops_remaining", 0)),
        },
    }


def predict_route_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_route_path()
    from route_predictor import orders_to_dataframe

    pred = get_route_predictor()
    route_df = orders_to_dataframe([o for o in payload["orders"]])
    sequence = pred.predict_full_sequence(route_df)
    return {"sequence": sequence}
