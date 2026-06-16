"""Courier route + ETA prediction service.

On-demand: fetch a courier's orders for a delivery day, run the route sequence
predictor, then estimate per-leg and cumulative ETA using the ETA model.
Returns a saved RoutePrediction from GraphDB when one exists for that day.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from aura_graphdb.aura_courier import get_courier_by_id
from aura_graphdb.aura_route_prediction import ensure_graph_courier_route, persist_ml_courier_route
from aura_graphdb.aura_route_queries import get_orders_for_courier_day, get_saved_courier_route
from ml_services.route_prediction.full_pipeline.coordinates import enrich_order_dict
from services.eta_prediction import predict_eta
from services.registry import get_route_predictor

ML_DEFAULT_DS = 318


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


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stop_point(stop: dict[str, Any], prefix: str) -> list[float] | None:
    lat = _float_or_none(stop.get(f"{prefix}_lat"))
    lng = _float_or_none(stop.get(f"{prefix}_lng"))
    if lat is None or lng is None:
        return None
    return [lat, lng]


def _courier_start_from_record(courier: dict[str, Any] | None, courier_id: str) -> dict[str, Any] | None:
    if not courier:
        return None
    lat = _float_or_none(courier.get("start_lat_wgs84"))
    lng = _float_or_none(courier.get("start_lon_wgs84"))
    if lat is None or lng is None:
        return None
    return {
        "lat": lat,
        "lng": lng,
        "name": courier.get("name") or courier_id,
    }


def build_route_path(
    stops: list[dict[str, Any]],
    courier_start: dict[str, Any] | None = None,
) -> list[list[float]]:
    """Build a map polyline from courier start through ordered hub legs."""
    path: list[list[float]] = []
    last: list[float] | None = None

    if courier_start and courier_start.get("lat") is not None and courier_start.get("lng") is not None:
        last = [float(courier_start["lat"]), float(courier_start["lng"])]
        path.append(last)

    for stop in sorted(stops, key=lambda s: int(s.get("sequence") or 0)):
        from_pt = _stop_point(stop, "from")
        to_pt = _stop_point(stop, "to")

        if not from_pt:
            lat = _float_or_none(stop.get("lat_wgs84"))
            lng = _float_or_none(stop.get("lon_wgs84"))
            if lat is not None and lng is not None:
                from_pt = [lat, lng]

        if not to_pt:
            to_pt = from_pt

        if from_pt and from_pt != last:
            path.append(from_pt)
            last = from_pt
        if to_pt and to_pt != last:
            path.append(to_pt)
            last = to_pt

    return path


def enrich_stops_with_geo(stops: list[dict[str, Any]], orders_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for stop in stops:
        order = orders_by_id.get(stop.get("order_id", ""), {})
        merged = dict(stop)
        merged.setdefault("from_hub_name", order.get("from_hub_name"))
        merged.setdefault("to_hub_name", order.get("to_hub_name"))
        merged["from_lat"] = _float_or_none(merged.get("from_lat")) or _float_or_none(order.get("from_lat"))
        merged["from_lng"] = (
            _float_or_none(merged.get("from_lng"))
            or _float_or_none(order.get("from_lon"))
            or _float_or_none(order.get("from_lng"))
        )
        merged["to_lat"] = _float_or_none(merged.get("to_lat")) or _float_or_none(order.get("to_lat"))
        merged["to_lng"] = (
            _float_or_none(merged.get("to_lng"))
            or _float_or_none(order.get("to_lon"))
            or _float_or_none(order.get("to_lng"))
        )
        merged["lat_wgs84"] = _float_or_none(merged.get("lat_wgs84")) or _float_or_none(order.get("lat_wgs84"))
        merged["lon_wgs84"] = _float_or_none(merged.get("lon_wgs84")) or _float_or_none(order.get("lon_wgs84"))
        enriched.append(merged)
    return enriched


def attach_map_geometry(
    payload: dict[str, Any],
    *,
    courier: dict[str, Any] | None = None,
    orders_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Add courier_start and path arrays for frontend map rendering."""
    courier_id = payload.get("courier_id", "")
    stops = list(payload.get("stops") or [])
    if orders_by_id:
        stops = enrich_stops_with_geo(stops, orders_by_id)

    courier_start = payload.get("courier_start")
    if not courier_start:
        if courier is None:
            courier = get_courier_by_id(courier_id)
        courier_start = _courier_start_from_record(courier, courier_id)

    path = build_route_path(stops, courier_start)
    payload["stops"] = stops
    payload["courier_start"] = courier_start
    payload["path"] = path
    return payload


def _format_saved_route(saved: dict[str, Any]) -> dict[str, Any]:
    """Normalize a GraphDB RoutePrediction into the API response shape."""
    stops = saved.get("stops") or []
    total_eta = saved.get("total_eta_minutes")
    if total_eta is None and stops:
        total_eta = sum(float(s.get("eta_minutes") or 0) for s in stops)

    route_start_time = saved.get("route_start_time")
    if not route_start_time:
        route_start_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "success": True,
        "courier_id": saved["courier_id"],
        "courier_name": saved.get("courier_name"),
        "delivery_day": saved["delivery_day"],
        "route_start_time": route_start_time,
        "predicted_sequence": saved.get("predicted_sequence") or [],
        "stops": stops,
        "total_eta_minutes": total_eta,
        "source": saved.get("source", "graphdb"),
        "courier_start": saved.get("courier_start"),
    }
    return attach_map_geometry(payload)


def predict_courier_route(
    courier_id: str,
    delivery_day: str,
) -> dict[str, Any]:
    """
    Return a complete courier route for a delivery day.

    Fix:
    - First fetch all currently assigned orders for the courier/date.
    - Use saved GraphDB route only if it contains the same order set.
    - If saved route is stale/incomplete, rebuild route using all assigned orders.
    """
    courier = get_courier_by_id(courier_id)
    if not courier:
        return {
            "success": False,
            "message": f"Courier {courier_id} not found.",
        }

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

    assigned_order_ids = {
        str(order.get("order_id"))
        for order in raw_orders
        if order.get("order_id")
    }

    saved = get_saved_courier_route(
        courier_id,
        delivery_day,
        ds=ML_DEFAULT_DS,
    )

    if saved and saved.get("stops"):
        saved_order_ids = {
            str(stop.get("order_id"))
            for stop in saved.get("stops", [])
            if stop.get("order_id")
        }

        if saved_order_ids == assigned_order_ids:
            return _format_saved_route(saved)

        print(
            "Saved route is stale/incomplete. "
            f"Courier={courier_id}, day={delivery_day}, "
            f"saved_stops={len(saved_order_ids)}, "
            f"assigned_orders={len(assigned_order_ids)}. "
            "Rebuilding route."
        )

    graph_result = ensure_graph_courier_route(
        courier_id=courier_id,
        delivery_day=delivery_day,
        ds=ML_DEFAULT_DS,
    )

    if graph_result.get("success") and graph_result.get("route"):
        route = graph_result["route"]
        route_stops = route.get("stops") or []

        graph_order_ids = {
            str(stop.get("order_id"))
            for stop in route_stops
            if stop.get("order_id")
        }

        if route_stops and graph_order_ids == assigned_order_ids:
            if graph_result.get("source") == "graphdb":
                return _format_saved_route(route)

            payload = {
                "success": True,
                "courier_id": courier_id,
                "courier_name": route.get("courier_name"),
                "delivery_day": delivery_day,
                "route_start_time": route.get("route_start_time"),
                "predicted_sequence": route.get("predicted_sequence") or [],
                "stops": route_stops,
                "total_eta_minutes": route.get("total_eta_minutes"),
                "source": route.get("source", "graph_built"),
            }

            return attach_map_geometry(payload, courier=courier)

        if route_stops:
            print(
                "Graph-built route is incomplete. "
                f"Courier={courier_id}, day={delivery_day}, "
                f"graph_stops={len(graph_order_ids)}, "
                f"assigned_orders={len(assigned_order_ids)}. "
                "Rebuilding with ML."
            )

    prepared = [enrich_order_dict(dict(o)) for o in raw_orders]
    orders_by_id = {o["order_id"]: o for o in prepared}

    try:
        predictor = get_route_predictor()
        route_df = _orders_to_predictor_df(prepared)
        predicted_sequence = predictor.predict_full_sequence(route_df)

        predicted_sequence = [
            order_id
            for order_id in predicted_sequence
            if order_id in orders_by_id
        ]

        missing_order_ids = [
            order_id
            for order_id in orders_by_id.keys()
            if order_id not in predicted_sequence
        ]

        if missing_order_ids:
            predicted_sequence.extend(missing_order_ids)

        route_source = "ml_model"

    except Exception as exc:
        print(f"ML route predictor unavailable. Using assigned-order fallback: {exc}")

        # Fallback: show all assigned orders in existing order sequence.
        # This prevents route modal from crashing when sklearn/model is missing.
        predicted_sequence = list(orders_by_id.keys())
        route_source = "graph_built"

    predicted_sequence = [
        order_id
        for order_id in predicted_sequence
        if order_id in orders_by_id
    ]

    missing_order_ids = [
        order_id
        for order_id in orders_by_id.keys()
        if order_id not in predicted_sequence
    ]

    if missing_order_ids:
        predicted_sequence.extend(missing_order_ids)

    route_start = datetime.now(ZoneInfo("Asia/Kolkata"))
    route_start_iso = route_start.strftime("%Y-%m-%d %H:%M:%S")

    start_lat = float(courier.get("start_lat_wgs84") or 0)
    start_lon = float(courier.get("start_lon_wgs84") or 0)
    prev_poi_lat, prev_poi_lng = _mercator_from_wgs84(start_lat, start_lon)

    cumulative_minutes = 0.0
    current_time = route_start

    stops: list[dict[str, Any]] = []
    geo_stops: list[dict[str, Any]] = []

    for seq, order_id in enumerate(predicted_sequence, start=1):
        order = orders_by_id[order_id]

        eta_payload = {
            "delivery_user_id": courier_id,
            "from_dipan_id": str(order.get("aoi_id", "")),
            "aoi_id": str(order.get("aoi_id", "")),
            "receipt_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "receipt_lat": prev_poi_lat,
            "receipt_lng": prev_poi_lng,
            "poi_lat": float(order["poi_lat"]),
            "poi_lng": float(order["poi_lng"]),
            "city_name": order.get("city_name", ""),
            "typecode": order.get("typecode", ""),
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
                "from_lat": _float_or_none(order.get("from_lat")),
                "from_lng": _float_or_none(order.get("from_lon")),
                "to_lat": _float_or_none(order.get("to_lat")),
                "to_lng": _float_or_none(order.get("to_lon")),
                "lat_wgs84": _float_or_none(order.get("lat_wgs84")),
                "lon_wgs84": _float_or_none(order.get("lon_wgs84")),
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

        prev_poi_lat = float(order["poi_lat"])
        prev_poi_lng = float(order["poi_lng"])

    total_eta = round(cumulative_minutes, 1)

    try:
        persist_ml_courier_route(
            courier_id=courier_id,
            city_name=city_name,
            ds=ML_DEFAULT_DS,
            delivery_day=delivery_day,
            order_ids=list(orders_by_id.keys()),
            predicted_sequence=predicted_sequence,
            stops=geo_stops,
            display_stops=stops,
            predicted_eta_min=total_eta,
        )
    except Exception as exc:
        print(f"Could not persist rebuilt courier route: {exc}")

    payload = {
        "success": True,
        "courier_id": courier_id,
        "courier_name": courier.get("name"),
        "delivery_day": delivery_day,
        "route_start_time": route_start_iso,
        "predicted_sequence": predicted_sequence,
        "stops": stops,
        "total_eta_minutes": total_eta,
        "source": route_source,
    }

    return attach_map_geometry(
        payload,
        courier=courier,
        orders_by_id=orders_by_id,
    )