"""Map Neo4j records into structured business results."""

from __future__ import annotations

from typing import Any


def _first_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    record = records[0]
    return record if isinstance(record, dict) else None


def _clean_route_stops(stops: Any) -> list[dict[str, Any]]:
    if not isinstance(stops, list):
        return []

    cleaned: list[dict[str, Any]] = []
    for stop in stops:
        if not isinstance(stop, dict):
            continue
        order_id = stop.get("order_id")
        if not order_id:
            continue
        cleaned.append(
            {
                "order_id": order_id,
                "sequence": stop.get("sequence"),
                "lat_wgs84": stop.get("lat_wgs84"),
                "lon_wgs84": stop.get("lon_wgs84"),
            }
        )
    return cleaned


class ResultMapper:
    """Convert raw graph records into task-specific structured results."""

    @staticmethod
    def map_result(task: str, records: list[dict[str, Any]]) -> dict[str, Any] | None:
        record = _first_record(records)
        if record is None:
            return None

        if task == "eta_lookup":
            order_id = record.get("order_id")
            eta_minutes = record.get("eta_minutes")
            if order_id is None or eta_minutes is None:
                return None
            return {
                "order_id": order_id,
                "eta_minutes": eta_minutes,
                "model_version": record.get("model_version"),
            }

        if task == "route_lookup":
            courier_id = record.get("courier_id")
            stops = _clean_route_stops(record.get("stops"))
            predicted_sequence = record.get("predicted_sequence")
            if courier_id is None:
                return None
            if not stops and not predicted_sequence:
                return None
            route = stops or [
                {"order_id": order_id, "sequence": index + 1}
                for index, order_id in enumerate(predicted_sequence or [])
            ]
            return {
                "courier_id": courier_id,
                "route_prediction_id": record.get("route_prediction_id"),
                "route": route,
                "predicted_sequence": predicted_sequence,
                "city_name": record.get("city_name"),
                "delivery_day": record.get("delivery_day"),
            }

        if task == "courier_lookup":
            courier_id = record.get("courier_id")
            if courier_id is None:
                return None
            return {
                "courier_id": courier_id,
                "name": record.get("name"),
                "email": record.get("email"),
                "hub_id": record.get("hub_id"),
                "hub_name": record.get("hub_name"),
                "city_name": record.get("city_name"),
                "role_name": record.get("role_name"),
            }

        if task == "shipment_lookup":
            order_id = record.get("order_id")
            if order_id is None:
                return None
            return {
                "order_id": order_id,
                "shipment_id": record.get("shipment_id") or order_id,
                "city_name": record.get("city_name"),
                "delivery_day": record.get("delivery_day"),
                "receipt_time": record.get("receipt_time"),
                "courier_id": record.get("courier_id") or record.get("assigned_courier_id"),
                "courier_name": record.get("courier_name"),
                "from_hub": record.get("from_hub"),
                "to_hub": record.get("to_hub"),
            }

        return None
