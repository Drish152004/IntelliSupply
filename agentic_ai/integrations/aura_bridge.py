"""Bridge from orchestrator to Aura GraphDB read operations."""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

from config.paths import REPO_ROOT

logger = logging.getLogger(__name__)

_AURA_ROOT = REPO_ROOT / "rag" / "aura_graphdb"
_imports_ready = False


def _ensure_aura_imports() -> None:
    global _imports_ready
    if _imports_ready:
        return
    root = str(REPO_ROOT)
    aura_path = str(_AURA_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    if aura_path not in sys.path:
        sys.path.insert(0, aura_path)
    _imports_ready = True


def list_cities() -> dict[str, Any]:
    _ensure_aura_imports()
    from aura_hubs import list_cities as fetch_cities  # noqa: WPS433

    cities = fetch_cities()
    return {
        "success": True,
        "answer": f"Found {len(cities)} cities with hubs.",
        "data": cities,
    }


def list_hubs(city_name: str | None = None) -> dict[str, Any]:
    _ensure_aura_imports()
    from aura_hubs import list_hubs as fetch_hubs  # noqa: WPS433

    hubs = fetch_hubs(city_name)
    label = f" in {city_name}" if city_name else ""
    return {
        "success": True,
        "answer": f"Found {len(hubs)} hubs{label}.",
        "data": hubs,
    }


def list_active_couriers(limit: int = 50) -> dict[str, Any]:
    _ensure_aura_imports()
    from aura_courier import list_active_couriers as fetch_couriers  # noqa: WPS433

    couriers = fetch_couriers(limit=limit)
    return {
        "success": True,
        "answer": f"Found {len(couriers)} active couriers.",
        "data": couriers,
    }


def get_saved_courier_route_for_entities(entities: dict[str, str]) -> dict[str, Any]:
    _ensure_aura_imports()
    from aura_route_queries import get_saved_courier_route  # noqa: WPS433

    courier_id = entities.get("courier_id")
    if not courier_id:
        return {"success": False, "answer": "Courier ID is required.", "data": None}

    delivery_day = entities.get("delivery_day") or str(date.today())
    route = get_saved_courier_route(courier_id, delivery_day)
    if not route:
        return {
            "success": False,
            "answer": f"No saved route for courier {courier_id} on {delivery_day}.",
            "data": None,
        }

    stops = route.get("stops") or []
    answer = (
        f"Route for courier {courier_id} on {delivery_day} has {len(stops)} stops"
        f" (ETA {route.get('total_eta_minutes')} min)."
    )
    return {"success": True, "answer": answer, "data": route}


def get_next_stop_for_entities(entities: dict[str, str]) -> dict[str, Any]:
    route_result = get_saved_courier_route_for_entities(entities)
    if not route_result.get("success"):
        return route_result

    route = route_result["data"] or {}
    stops = route.get("stops") or []
    if not stops:
        return {
            "success": False,
            "answer": "No stops found on the saved route.",
            "data": route,
        }

    ordered = sorted(stops, key=lambda s: s.get("sequence", 0))
    next_stop = ordered[0]
    order_id = next_stop.get("order_id", "unknown")
    answer = f"Next stop is order {order_id} (sequence {next_stop.get('sequence', 1)})."
    return {"success": True, "answer": answer, "data": {"next_stop": next_stop, "route": route}}


def query_logistics(
    *,
    user_query: str,
    task: str,
    entities: dict[str, str],
) -> dict[str, Any]:
    """Execute a logistics retrieval against Aura GraphDB based on task and entities."""
    _ensure_aura_imports()

    from aura_route_queries import (  # noqa: WPS433
        answer_route_question,
        get_order_route,
        get_orders_for_courier,
        get_recent_order_routes,
    )

    try:
        if task == "city_lookup":
            return list_cities()

        if task == "hub_lookup":
            return list_hubs(entities.get("city_name"))

        if task == "courier_route_lookup":
            return get_saved_courier_route_for_entities(entities)

        if task == "next_stop_lookup":
            return get_next_stop_for_entities(entities)

        if task == "route_lookup":
            order_id = entities.get("order_id")
            if order_id:
                route = get_order_route(order_id)
                if route:
                    answer = (
                        f"Order {route['order_id']} goes from {route.get('from_hub_name')} "
                        f"to {route.get('to_hub_name')}."
                    )
                    return {"success": True, "answer": answer, "data": route}
                return {
                    "success": False,
                    "answer": f"No route found for order {order_id}.",
                    "data": None,
                }
            courier_id = entities.get("courier_id")
            if courier_id:
                return get_saved_courier_route_for_entities(entities)
            return answer_route_question(user_query)

        if task == "eta_lookup":
            order_id = entities.get("order_id") or entities.get("shipment_id")
            if order_id:
                route = get_order_route(order_id)
                if route:
                    eta_info = {
                        "order_id": route.get("order_id"),
                        "receipt_time": str(route.get("receipt_time", "")),
                        "delivery_day": route.get("delivery_day"),
                        "from_hub": route.get("from_hub_name"),
                        "to_hub": route.get("to_hub_name"),
                    }
                    answer = (
                        f"Order {order_id} receipt time is {eta_info['receipt_time']} "
                        f"with delivery day {eta_info.get('delivery_day')}."
                    )
                    return {"success": True, "answer": answer, "data": eta_info}
                return {
                    "success": False,
                    "answer": f"No ETA information found for {order_id}.",
                    "data": None,
                }
            if entities.get("courier_id"):
                route_result = get_saved_courier_route_for_entities(entities)
                if route_result.get("success"):
                    data = route_result["data"]
                    answer = f"Courier route ETA is {data.get('total_eta_minutes')} minutes."
                    return {"success": True, "answer": answer, "data": data}
                return route_result
            return answer_route_question(user_query)

        if task == "courier_lookup":
            courier_id = entities.get("courier_id")
            if courier_id:
                from aura_courier import get_courier_by_id as fetch_courier  # noqa: WPS433

                courier = fetch_courier(courier_id)
                if courier:
                    answer = (
                        f"Courier {courier.get('name')} ({courier_id}) "
                        f"hub: {courier.get('hub_name')}."
                    )
                    return {"success": True, "answer": answer, "data": courier}
                return {
                    "success": False,
                    "answer": f"No courier found with ID {courier_id}.",
                    "data": None,
                }
            if "active" in user_query.lower():
                return list_active_couriers()
            return {"success": False, "answer": "Please provide a courier ID.", "data": None}

        if task == "shipment_lookup":
            order_id = entities.get("order_id") or entities.get("shipment_id")
            if order_id:
                route = get_order_route(order_id)
                if route:
                    answer = (
                        f"Shipment/order {order_id} is assigned to courier "
                        f"{route.get('assigned_courier_name')} "
                        f"({route.get('assigned_courier_id')})."
                    )
                    return {"success": True, "answer": answer, "data": route}
                return {
                    "success": False,
                    "answer": f"No shipment found for {order_id}.",
                    "data": None,
                }

            courier_id = entities.get("courier_id")
            if courier_id:
                orders = get_orders_for_courier(courier_id, limit=10)
                return {
                    "success": True,
                    "answer": f"Found {len(orders)} orders for courier {courier_id}.",
                    "data": orders,
                }

            if "recent" in user_query.lower() or "latest" in user_query.lower():
                routes = get_recent_order_routes(limit=10)
                return {
                    "success": True,
                    "answer": f"Found {len(routes)} recent shipments.",
                    "data": routes,
                }

            return answer_route_question(user_query)

        return answer_route_question(user_query)

    except Exception as exc:
        logger.exception("Aura logistics query failed")
        return {
            "success": False,
            "answer": f"Logistics lookup failed: {exc}",
            "data": None,
            "error": str(exc),
        }
