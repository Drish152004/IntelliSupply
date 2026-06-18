"""Bridge from orchestrator to Aura GraphDB read operations."""

from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path
from typing import Any

from config.paths import REPO_ROOT
from observability.prompt_capture import capture_prompt
from observability.trace_events import (
    get_current_trace_id,
    summarize_graph_records,
    trace_graph_cypher,
    trace_graph_request,
    trace_graph_result,
)

logger = logging.getLogger(__name__)

_AURA_ROOT = REPO_ROOT / "rag" / "aura_graphdb"
_imports_ready = False
_graph_observer_registered = False


def _register_graph_observer() -> None:
    global _graph_observer_registered
    if _graph_observer_registered:
        return
    _ensure_aura_imports()
    from aura_connection import register_graph_query_observer  # noqa: WPS433

    def _observer(query: str, parameters: dict[str, Any]) -> None:
        trace_graph_cypher(
            {"cypher": query.strip(), "parameters": parameters},
            trace_id=get_current_trace_id(),
        )

    register_graph_query_observer(_observer)
    _graph_observer_registered = True


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


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _estimate_time_minutes(distance_km: float) -> int:
    return max(5, int(round(distance_km * 3.0)))


def fetch_order_route(order_id: str) -> dict[str, Any] | None:
    """Load order route metadata from Aura (authorization and logistics queries)."""
    _ensure_aura_imports()
    from aura_route_queries import get_order_route  # noqa: WPS433

    return get_order_route(order_id)


def execute_aura_function(
    *,
    function_name: str,
    payload: dict[str, Any],
    user_query: str = "",
    prefetched_order_route: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Execute a single Aura GraphDB function selected by parameter preparation."""
    _ensure_aura_imports()
    _register_graph_observer()

    resolved_trace_id = trace_id or get_current_trace_id()
    graph_prompt = (
        f"Function: {function_name}\n"
        f"Question: {user_query}\n"
        f"Payload: {json.dumps(payload, default=str)}"
    )
    capture_prompt(resolved_trace_id or "unknown", "graphrag_prompt", graph_prompt)
    trace_graph_request(
        {
            "question": user_query,
            "function_name": function_name,
            "payload": payload,
        },
        trace_id=resolved_trace_id,
    )

    try:
        result = _dispatch_aura_function(
            function_name=function_name,
            payload=payload,
            prefetched_order_route=prefetched_order_route,
        )
    except Exception as exc:
        logger.exception("Aura function %s failed", function_name)
        result = {
            "success": False,
            "data": None,
            "error": str(exc),
        }

    trace_graph_result(
        summarize_graph_records(result.get("data")),
        trace_id=resolved_trace_id,
    )
    return result


def _dispatch_aura_function(
    *,
    function_name: str,
    payload: dict[str, Any],
    prefetched_order_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from aura_hubs import resolve_hub  # noqa: WPS433
    from aura_route_queries import (  # noqa: WPS433
        get_order_route,
        get_orders_for_courier,
        get_orders_for_courier_day,
        get_recent_order_routes,
        get_saved_courier_route,
        list_delivery_days_with_orders,
    )

    if function_name == "get_order_route":
        order_id = str(payload.get("order_id", "")).strip()
        route = prefetched_order_route
        if route and str(route.get("order_id")) != order_id:
            route = None
        if route is None:
            route = get_order_route(order_id)
        if route:
            return {"success": True, "data": route, "summary": "Order found"}
        return {
            "success": False,
            "data": None,
            "summary": "Order not found",
        }

    if function_name == "get_orders_for_courier":
        courier_id = str(payload.get("courier_id", "")).strip()
        orders = get_orders_for_courier(courier_id, limit=20)
        return {
            "success": True,
            "data": orders,
            "summary": f"{len(orders)} orders",
        }

    if function_name == "get_orders_for_courier_day":
        courier_id = str(payload.get("courier_id", "")).strip()
        delivery_day = str(payload.get("delivery_day", "")).strip()
        orders = get_orders_for_courier_day(
            courier_id=courier_id,
            city_name="",
            delivery_day=delivery_day,
        )
        return {
            "success": True,
            "data": orders,
            "summary": f"{len(orders)} orders",
        }

    if function_name == "get_saved_courier_route":
        courier_id = str(payload.get("courier_id", "")).strip()
        delivery_day = str(payload.get("delivery_day", "")).strip()
        route = get_saved_courier_route(courier_id, delivery_day)
        if not route:
            return {
                "success": False,
                "data": None,
                "summary": "Saved route not found",
                "error": "No saved route found for this courier and delivery day.",
            }
        return {"success": True, "data": route, "summary": "Saved route found"}

    if function_name == "get_recent_order_routes":
        courier_id = payload.get("courier_id")
        delivery_day = payload.get("delivery_day")
        limit = payload.get("limit", 20)
        try:
            limit_value = int(limit)
        except (TypeError, ValueError):
            limit_value = 20
        routes = get_recent_order_routes(
            limit=limit_value,
            courier_id=str(courier_id).strip() if courier_id else None,
            delivery_day=str(delivery_day).strip() if delivery_day else None,
        )
        return {
            "success": True,
            "data": routes,
            "summary": f"{len(routes)} routes",
        }

    if function_name == "list_delivery_days_with_orders":
        days = list_delivery_days_with_orders(limit=30)
        return {
            "success": True,
            "data": days,
            "summary": f"{len(days)} delivery days",
        }

    if function_name == "resolve_route_hubs":
        from_hub_id = int(payload["from_hub_id"])
        to_hub_id = int(payload["to_hub_id"])
        from_hub = resolve_hub(hub_id=from_hub_id)
        to_hub = resolve_hub(hub_id=to_hub_id)
        if not from_hub:
            return {
                "success": False,
                "data": None,
                "summary": "From hub not found",
            }
        if not to_hub:
            return {
                "success": False,
                "data": None,
                "summary": "To hub not found",
            }

        from_name = from_hub.get("name") or from_hub.get("hub_name") or str(from_hub_id)
        to_name = to_hub.get("name") or to_hub.get("hub_name") or str(to_hub_id)
        from_lat = from_hub.get("lat")
        from_lng = from_hub.get("lng")
        to_lat = to_hub.get("lat")
        to_lng = to_hub.get("lng")

        distance_km = None
        estimated_time_min = None
        if None not in (from_lat, from_lng, to_lat, to_lng):
            distance_km = round(
                _haversine_km(float(from_lat), float(from_lng), float(to_lat), float(to_lng)),
                2,
            )
            estimated_time_min = _estimate_time_minutes(distance_km)

        return {
            "success": True,
            "data": {
                "from_hub": from_hub,
                "to_hub": to_hub,
                "distance": {
                    "map_distance_km": distance_km,
                    "estimated_time_min": estimated_time_min,
                    "from_hub_name": from_name,
                    "to_hub_name": to_name,
                },
            },
            "summary": "Route hubs resolved",
        }

    return {
        "success": False,
        "data": None,
        "error_code": "UNKNOWN_FUNCTION",
    }
