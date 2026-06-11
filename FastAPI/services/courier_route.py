"""Courier route + ETA prediction service.

On-demand: fetch a courier's orders for a delivery day, run the route sequence
predictor, then estimate per-leg and cumulative ETA using the ETA model.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from aura_graphdb.aura_courier import get_courier_by_id
from aura_graphdb.aura_route_prediction import persist_ml_courier_route
from aura_graphdb.aura_route_queries import get_orders_for_courier_day
from aura_graphdb.hub_coordinates import ML_DEFAULT_DS
from ml_services.route_prediction.full_pipeline.coordinates import enrich_order_dict
from services.eta_prediction import predict_eta
from services.registry import get_route_predictor


def _orders_to_predictor_df(orders: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [
        {
            "order_id": o["order_id"],
            "poi_lat": o["poi_lat"],
            "poi_lng": o["poi_lng"],
            "receipt_time": o["receipt_time"],
            "receipt_lat": o["receipt_lat"],
            "receipt_lng": o["receipt_lng"],
            "city_name": o["city_name"],
            "typecode": o["typecode"],
            "aoi_id": o["aoi_id"],
        }
        for o in orders
    ]
    return pd.DataFrame(rows)


def _mercator_from_wgs84(lat_wgs84: float, lon_wgs84: float) -> tuple[float, float]:
    """Convert WGS84 to Web Mercator (poi_lat, poi_lng) for ETA model input."""
    dummy = {
        "lat_wgs84": lat_wgs84,
        "lon_wgs84": lon_wgs84,
        "receipt_lat_wgs84": lat_wgs84,
        "receipt_lon_wgs84": lon_wgs84,
    }
    enriched = enrich_order_dict(dummy)
    return float(enriched["poi_lat"]), float(enriched["poi_lng"])


def predict_courier_route(
    courier_id: str,
    delivery_day: str,
) -> dict[str, Any]:
    """Predict delivery sequence and per-leg ETA for a courier on a given day.

    Args:
        courier_id: The courier's graph ID.
        delivery_day: ISO date string (YYYY-MM-DD).

    Returns:
        Dict with courier_id, delivery_day, predicted_sequence, stops (ordered),
        total_eta_minutes, and route_start_time.
    """
    courier = get_courier_by_id(courier_id)
    if not courier:
        return {"success": False, "message": f"Courier {courier_id} not found."}

    city_name = courier.get("city_name") or ""

    raw_orders = get_orders_for_courier_day(
        courier_id=courier_id,
        city_name=city_name,
        delivery_day=delivery_day,
    )
    if not raw_orders:
        return {
            "success": False,
            "message": f"No orders found for courier {courier_id} on {delivery_day}.",
        }

    prepared = [enrich_order_dict(dict(o)) for o in raw_orders]
    orders_by_id = {o["order_id"]: o for o in prepared}

    predictor = get_route_predictor()
    route_df = _orders_to_predictor_df(prepared)
    predicted_sequence = predictor.predict_full_sequence(route_df)

    # ETA chain — start at route_start_time (current IST), courier hub as first origin
    route_start = datetime.now(ZoneInfo("Asia/Kolkata"))
    route_start_iso = route_start.strftime("%Y-%m-%d %H:%M:%S")

    # Courier hub WGS84 → Mercator for first-leg receipt
    start_lat = float(courier.get("start_lat_wgs84") or 0)
    start_lon = float(courier.get("start_lon_wgs84") or 0)
    prev_poi_lat, prev_poi_lng = _mercator_from_wgs84(start_lat, start_lon)

    cumulative_minutes = 0.0
    current_time = route_start
    stops: list[dict[str, Any]] = []
    geo_stops: list[dict[str, Any]] = []

    for seq, order_id in enumerate(predicted_sequence, start=1):
        order = orders_by_id[order_id]

        # from_hub_id stored on order as aoi_id (used as from_dipan_id in ETA model)
        eta_payload = {
            "delivery_user_id": courier_id,
            "from_dipan_id": str(order.get("aoi_id", "")),
            "aoi_id": str(order.get("aoi_id", "")),
            "receipt_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "receipt_lat": prev_poi_lat,
            "receipt_lng": prev_poi_lng,
            "poi_lat": float(order["poi_lat"]),
            "poi_lng": float(order["poi_lng"]),
        }

        try:
            eta_result = predict_eta(eta_payload)
            leg_minutes = float(eta_result.get("eta_minutes", 30))
        except Exception:
            leg_minutes = 30.0

        cumulative_minutes += leg_minutes
        current_time = route_start + timedelta(minutes=cumulative_minutes)

        stops.append(
            {
                "sequence": seq,
                "order_id": order_id,
                "from_hub_name": order.get("from_hub_name"),
                "to_hub_name": order.get("to_hub_name"),
                "city_name": order.get("city_name"),
                "delivery_day": order.get("delivery_day"),
                "eta_minutes": round(leg_minutes, 1),
                "eta_from_start_minutes": round(cumulative_minutes, 1),
                "estimated_arrival": current_time.strftime("%H:%M"),
            }
        )
        geo_stops.append(
            {
                "sequence": seq,
                "order_id": order_id,
                "lat_wgs84": float(order["lat_wgs84"]),
                "lon_wgs84": float(order["lon_wgs84"]),
            }
        )

        # Next leg starts from this delivery point
        prev_poi_lat = float(order["poi_lat"])
        prev_poi_lng = float(order["poi_lng"])

    total_eta = round(cumulative_minutes, 1)

    # Persist the prediction (fixes the missing predicted_eta_min bug)
    try:
        persist_ml_courier_route(
            courier_id=courier_id,
            city_name=city_name,
            ds=ML_DEFAULT_DS,
            delivery_day=delivery_day,
            order_ids=list(orders_by_id.keys()),
            predicted_sequence=predicted_sequence,
            stops=geo_stops,
            predicted_eta_min=total_eta,
        )
    except Exception:
        pass  # Persistence failure should not block the response

    return {
        "success": True,
        "courier_id": courier_id,
        "courier_name": courier.get("name"),
        "delivery_day": delivery_day,
        "route_start_time": route_start_iso,
        "predicted_sequence": predicted_sequence,
        "stops": stops,
        "total_eta_minutes": total_eta,
    }
