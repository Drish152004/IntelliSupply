"""Persist ML route prediction results into Neo4j Aura."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.aura_route_queries import build_route_stops_from_orders, get_orders_for_courier_day
from rag.aura_graphdb.shared_cypher import PERSIST_ASSIGNED_ROUTE_QUERY
from rag.aura_graphdb.shared_cypher import DELETE_ROUTE_PREDICTION_QUERY
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

        if predicted_eta_min is not None and predicted_eta_min >= 250:
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


def delete_ml_courier_route(
    *,
    courier_id: str,
    delivery_day: str | None = None,
    ds: int = DEFAULT_DS,
) -> dict[str, Any]:
    """Delete a persisted RoutePrediction for a courier on a delivery day.

    Returns a dict with success/message/deleted_count.
    """
    conn = AuraConnection()
    route_prediction_ids = [f"{courier_id}_{ds}_{delivery_day}", f"{courier_id}_{delivery_day}"]
    params = {
        "courier_id": courier_id,
        "delivery_day": delivery_day,
        "route_prediction_ids": route_prediction_ids,
    }
    try:
        rows = conn.execute_write(DELETE_ROUTE_PREDICTION_QUERY, params)
        deleted = 0
        try:
            if isinstance(rows, list) and rows:
                deleted = int(rows[0].get("deleted_count", 0) or 0)
        except Exception:
            deleted = 0
        return {"success": True, "message": "Deleted persisted route prediction.", "deleted_count": deleted}
    except Exception as exc:
        return {"success": False, "message": str(exc), "deleted_count": 0}
    finally:
        conn.close()


def ensure_graph_courier_route(
    *,
    courier_id: str,
    delivery_day: str,
    city_name: str | None = None,
    ds: int = DEFAULT_DS,
) -> dict[str, Any]:
    """Build and persist a graph-sorted courier route from assigned Aura orders (no ML).

    Standalone utility for callers that need graph-only route building. Not used by
    predict_courier_route(), which validates a saved route then falls through to ML.
    """
    from aura_graphdb.aura_courier import get_courier_by_id
    from aura_graphdb.aura_route_queries import get_saved_courier_route

    saved = get_saved_courier_route(courier_id, delivery_day, ds=ds)
    if saved and saved.get("stops"):
        return {"success": True, "source": "graphdb", "route": saved}

    courier = get_courier_by_id(courier_id)
    if not courier:
        return {"success": False, "message": f"Courier {courier_id} not found."}

    resolved_city = (city_name or courier.get("city_name") or "").strip()
    raw_orders = get_orders_for_courier_day(
        courier_id=courier_id,
        city_name=resolved_city,
        delivery_day=delivery_day,
    )
    if not raw_orders and resolved_city:
        raw_orders = get_orders_for_courier_day(
            courier_id=courier_id,
            city_name="",
            delivery_day=delivery_day,
        )

    if not raw_orders:
        return {
            "success": False,
            "message": f"No orders found for courier {courier_id} on {delivery_day}.",
        }

    built = build_route_stops_from_orders([dict(o) for o in raw_orders], courier)
    persist_result = persist_ml_courier_route(
        courier_id=courier_id,
        order_ids=built["order_ids"],
        predicted_sequence=built["predicted_sequence"],
        stops=built["geo_stops"],
        display_stops=built["stops"],
        predicted_eta_min=built["total_eta_minutes"],
        ds=ds,
        city_name=resolved_city or built.get("city_name"),
        delivery_day=delivery_day,
    )
    if not persist_result.get("success"):
        return persist_result

    saved = get_saved_courier_route(courier_id, delivery_day, ds=ds)
    if saved and saved.get("stops"):
        return {"success": True, "source": "graphdb", "route": saved}

    return {
        "success": True,
        "source": "graph_built",
        "route": {
            "courier_id": courier_id,
            "courier_name": courier.get("name"),
            "delivery_day": delivery_day,
            "predicted_sequence": built["predicted_sequence"],
            "stops": built["stops"],
            "total_eta_minutes": built["total_eta_minutes"],
            "route_start_time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            "source": "graph_built",
        },
    }