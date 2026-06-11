"""Persist ML route prediction results into Neo4j Aura."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aura_graphdb.aura_connection import AuraConnection
from rag.aura_graphdb.shared_cypher import PERSIST_ASSIGNED_ROUTE_QUERY
from rag.supabase.supabase_notifications import create_notification

DEFAULT_DS = 318


def _safe_create_notification(**kwargs):
    try:
        create_notification(**kwargs)
    except Exception as exc:
        print(f"Notification create failed: {exc}")


def persist_ml_courier_route(
    *,
    courier_id: str,
    order_ids: list[str],
    predicted_sequence: list[str],
    stops: list[dict[str, Any]],
    predicted_eta_min: float | None,
    ds: int = DEFAULT_DS,
    city_name: str | None = None,
    delivery_day: str | None = None,
    display_stops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist route prediction output after the ML model runs."""
    conn = AuraConnection()

    route_prediction_id = f"{courier_id}_{ds}"
    if delivery_day:
        route_prediction_id = f"{courier_id}_{ds}_{delivery_day}"

    route_start_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    route = {
        "route_prediction_id": route_prediction_id,
        "courier_id": courier_id,
        "order_ids": order_ids,
        "predicted_sequence": predicted_sequence,
        "stops": stops,
        "predicted_stops_json": json.dumps(stops),
        "stops_json": json.dumps(display_stops) if display_stops else None,
        "predicted_eta_min": predicted_eta_min,
        "ds": int(ds),
        "city_name": city_name,
        "delivery_day": delivery_day,
        "route_start_time": route_start_time,
    }

    try:
        conn.execute_write(PERSIST_ASSIGNED_ROUTE_QUERY, {"routes": [route]})

        route_prediction = {
            "route_prediction_id": route_prediction_id,
            "courier_id": courier_id,
            "order_ids": order_ids,
            "predicted_sequence": predicted_sequence,
            "stops": stops,
            "predicted_eta_min": predicted_eta_min,
            "ds": int(ds),
            "city_name": city_name,
            "delivery_day": delivery_day,
            "stop_count": len(stops),
        }

        for role in ["admin", "logistics_manager"]:
            _safe_create_notification(
                title="Route prediction completed",
                message=(
                    f"Route prediction completed for courier {courier_id} "
                    f"with {len(stops)} stops."
                ),
                alert_type="route_prediction_completed",
                severity="medium",
                target_role=role,
                related_entity_type="route_prediction",
                related_entity_id=route_prediction_id,
                source="graphdb",
                dedupe_key=f"route_prediction_completed:{route_prediction_id}:{role}",
            )

        if predicted_eta_min is not None and predicted_eta_min >= 60:
            for role in ["admin", "logistics_manager"]:
                _safe_create_notification(
                    title="High ETA predicted",
                    message=(
                        f"Predicted ETA for courier {courier_id} is "
                        f"{predicted_eta_min:.1f} minutes."
                    ),
                    alert_type="high_eta_prediction",
                    severity="high",
                    target_role=role,
                    related_entity_type="route_prediction",
                    related_entity_id=route_prediction_id,
                    source="ml_model",
                    dedupe_key=f"high_eta_prediction:{route_prediction_id}:{role}",
                )

        return {
            "success": True,
            "message": "Route prediction persisted successfully.",
            "route_prediction": route_prediction,
        }

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc),
            "route_prediction": None,
        }

    finally:
        conn.close()