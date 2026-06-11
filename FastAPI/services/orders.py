"""Order creation and route prediction orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from aura_graphdb.hub_coordinates import ML_DEFAULT_DS
from aura_graphdb.aura_order import create_order_and_assign_nearest_courier
from aura_graphdb.aura_route_prediction import persist_ml_courier_route
from aura_graphdb.aura_route_queries import get_orders_for_courier_day
from ml_services.route_prediction.full_pipeline.coordinates import enrich_order_dict
from services.registry import get_route_predictor


def _resolve_receipt_time(delivery_date: str, receipt_time: str | None) -> str:
    if receipt_time:
        return f"{delivery_date} {receipt_time}"
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")


def _orders_to_predictor_df(orders: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for order in orders:
        rows.append(
            {
                "order_id": order["order_id"],
                "poi_lat": order["poi_lat"],
                "poi_lng": order["poi_lng"],
                "receipt_time": order["receipt_time"],
                "receipt_lat": order["receipt_lat"],
                "receipt_lng": order["receipt_lng"],
                "city_name": order["city_name"],
                "typecode": order["typecode"],
                "aoi_id": order["aoi_id"],
            }
        )
    return pd.DataFrame(rows)


def _build_stops(sequence: list[str], orders_by_id: dict[str, dict]) -> list[dict[str, Any]]:
    stops = []
    for seq, order_id in enumerate(sequence, start=1):
        order = orders_by_id[order_id]
        stops.append(
            {
                "sequence": seq,
                "order_id": order_id,
                "lat_wgs84": order["lat_wgs84"],
                "lon_wgs84": order["lon_wgs84"],
            }
        )
    return stops


def _predict_and_persist_route(order: dict[str, Any]) -> tuple[dict | None, str | None]:
    courier_id = order["assigned_courier_id"]
    city_name = order["city_name"]
    delivery_day = order["delivery_day"]

    raw_orders = get_orders_for_courier_day(
        courier_id=courier_id,
        city_name=city_name,
        delivery_day=delivery_day,
    )
    if not raw_orders:
        return None, "No orders found for courier after creation."

    prepared = [enrich_order_dict(dict(row)) for row in raw_orders]
    orders_by_id = {row["order_id"]: row for row in prepared}

    predictor = get_route_predictor()
    route_df = _orders_to_predictor_df(prepared)
    predicted_sequence = predictor.predict_full_sequence(route_df)
    stops = _build_stops(predicted_sequence, orders_by_id)
    order_ids = [row["order_id"] for row in prepared]

    result = persist_ml_courier_route(
        courier_id=courier_id,
        city_name=city_name,
        ds=ML_DEFAULT_DS,
        delivery_day=delivery_day,
        order_ids=order_ids,
        predicted_sequence=predicted_sequence,
        stops=stops,
    )

    if not result.get("success"):
        return None, result.get("message", "Route prediction persistence failed.")

    return result["route_prediction"], None


def _sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in record.items():
        if value is None:
            out[key] = None
        elif hasattr(value, "iso_format"):
            out[key] = value.iso_format()
        elif hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def create_shipment(payload: dict[str, Any]) -> dict[str, Any]:
    receipt_time = _resolve_receipt_time(payload["delivery_date"], payload.get("receipt_time"))

    order_result = create_order_and_assign_nearest_courier(
        from_hub_name=payload["from_hub_name"],
        to_hub_name=payload["to_hub_name"],
        delivery_day=payload["delivery_date"],
        receipt_time=receipt_time,
        extra_notes=payload.get("notes"),
    )

    if not order_result.get("success"):
        return {
            "success": False,
            "message": order_result.get("message", "Order creation failed."),
            "order": None,
            "route_prediction": None,
            "route_error": None,
        }

    order = _sanitize_record(order_result["order"])
    route_prediction = None
    route_error = None

    try:
        route_prediction, route_error = _predict_and_persist_route(order)
    except FileNotFoundError as exc:
        route_error = str(exc)
    except Exception as exc:
        route_error = str(exc)

    message = order_result["message"]
    if route_error:
        message = f"{message} Route prediction skipped: {route_error}"

    return {
        "success": True,
        "message": message,
        "order": order,
        "route_prediction": route_prediction,
        "route_error": route_error,
    }
