import json
import uuid
from typing import Any, Dict, Optional

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.aura_route_cypher import PERSIST_ASSIGNED_ROUTE_QUERY


def store_route_prediction(
    courier_id: str,
    input_features: Dict[str, Any],
    predicted_eta_min: Optional[float] = None,
    predicted_route: Optional[str] = None,
    delay_probability: Optional[float] = None,
    risk_level: Optional[str] = None,
    model_version: str = "route_model_v1"
):
    conn = AuraConnection()

    route_prediction_id = uuid.uuid4().hex

    query = """
    MATCH (courier:Courier {courier_id: $courier_id})
    OPTIONAL MATCH (courier)-[:ASSIGNED_TO_HUB]->(hub:Hub)

    CREATE (rp:RoutePrediction {
        route_prediction_id: $route_prediction_id,
        courier_id: $courier_id,
        input_features_json: $input_features_json,
        predicted_eta_min: $predicted_eta_min,
        predicted_route: $predicted_route,
        delay_probability: $delay_probability,
        risk_level: $risk_level,
        model_version: $model_version,
        created_at: datetime()
    })

    MERGE (rp)-[:FOR_COURIER]->(courier)

    FOREACH (_ IN CASE WHEN hub IS NULL THEN [] ELSE [1] END |
        MERGE (rp)-[:STARTS_FROM]->(hub)
    )

    RETURN
        rp.route_prediction_id AS route_prediction_id,
        rp.courier_id AS courier_id,
        rp.predicted_eta_min AS predicted_eta_min,
        rp.predicted_route AS predicted_route,
        rp.delay_probability AS delay_probability,
        rp.risk_level AS risk_level,
        rp.model_version AS model_version
    """

    try:
        result = conn.execute_write(query, {
            "route_prediction_id": route_prediction_id,
            "courier_id": courier_id,
            "input_features_json": json.dumps(input_features),
            "predicted_eta_min": predicted_eta_min,
            "predicted_route": predicted_route,
            "delay_probability": delay_probability,
            "risk_level": risk_level,
            "model_version": model_version
        })

        if not result:
            return {
                "success": False,
                "message": "Courier not found."
            }

        return {
            "success": True,
            "message": "Route prediction stored successfully.",
            "route_prediction": result[0]
        }

    finally:
        conn.close()


def persist_ml_courier_route(
    courier_id: str,
    cluster_id: int,
    city_name: str,
    ds: int,
    delivery_day: str,
    order_ids: list[str],
    predicted_sequence: list[str],
    stops: list[dict[str, Any]],
) -> dict:
    """Upsert RoutePrediction + HAS_STOP edges for a courier's predicted route."""
    conn = AuraConnection()

    route = {
        "courier_id": courier_id,
        "cluster_id": int(cluster_id),
        "city_name": city_name,
        "ds": int(ds),
        "delivery_day": delivery_day,
        "order_ids": order_ids,
        "predicted_sequence": predicted_sequence,
        "stops": stops,
    }

    route_prediction_id = f"{courier_id}_{ds}_{delivery_day}"

    try:
        conn.execute_write(PERSIST_ASSIGNED_ROUTE_QUERY, {"routes": [route]})

        return {
            "success": True,
            "message": "Route prediction persisted successfully.",
            "route_prediction": {
                "route_prediction_id": route_prediction_id,
                "courier_id": courier_id,
                "cluster_id": int(cluster_id),
                "city_name": city_name,
                "ds": int(ds),
                "delivery_day": delivery_day,
                "order_ids": order_ids,
                "predicted_sequence": predicted_sequence,
                "stops": stops,
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