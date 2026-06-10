"""Persist ML route prediction results into Neo4j Aura."""

from __future__ import annotations
import json
from typing import Any
from aura_graphdb.aura_connection import AuraConnection
from rag.aura_graphdb.shared_cypher import PERSIST_ASSIGNED_ROUTE_QUERY

def persist_ml_courier_route(
    *,
    courier_id: str,
    order_ids: list[str],
    predicted_sequence: list[str],
    stops: list[dict[str, Any]],
    predicted_eta_min: float | None,
    ds: int,
    city_name: str | None = None,
    delivery_day: str | None = None,
    cluster_id: int | None = None,
) -> dict[str, Any]:
    """
    Persist route prediction output after the ML model runs.

    Stores:
    - courier_id
    - order_ids
    - predicted route sequence
    - predicted stops
    - predicted ETA
    - ds
    """
    conn = AuraConnection()

    route_prediction_id = f"{courier_id}_{ds}"
    if delivery_day:
        route_prediction_id = f"{courier_id}_{ds}_{delivery_day}"

    route = {
        "route_prediction_id": route_prediction_id,
        "courier_id": courier_id,
        "order_ids": order_ids,
        "predicted_sequence": predicted_sequence,
        "stops": stops,
        "predicted_stops_json": json.dumps(stops),
        "predicted_eta_min": predicted_eta_min,
        "ds": int(ds),
        "city_name": city_name,
        "delivery_day": delivery_day,
        "cluster_id": cluster_id,
    }

    try:
        conn.execute_write(PERSIST_ASSIGNED_ROUTE_QUERY, {"routes": [route]})

        return {
            "success": True,
            "message": "Route prediction persisted successfully.",
            "route_prediction": {
                "route_prediction_id": route_prediction_id,
                "courier_id": courier_id,
                "order_ids": order_ids,
                "predicted_sequence": predicted_sequence,
                "stops": stops,
                "predicted_eta_min": predicted_eta_min,
                "ds": int(ds),
                "city_name": city_name,
                "delivery_day": delivery_day,
                "cluster_id": cluster_id,
                "stop_count": len(stops),
            },
        }

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc),
            "route_prediction": None,
        }

    finally:
        conn.close()