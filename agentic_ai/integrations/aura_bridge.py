"""Bridge from orchestrator to Aura GraphDB read operations."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from config.paths import REPO_ROOT
from context.query_completeness_checker import QueryCompletenessChecker
from observability.prompt_capture import capture_prompt
from observability.trace_events import (
    get_current_trace_id,
    summarize_graph_records,
    trace_graph_cypher,
    trace_graph_request,
    trace_graph_result,
)
from orchestrator.task_registry import QUERY_ENTITY_REQUIREMENTS

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


def _resolve_delivery_day(entities: dict[str, str]) -> str:
    """Use extracted delivery_day when present; otherwise default to today."""
    explicit = (entities or {}).get("delivery_day")
    if explicit:
        return explicit
    return str(date.today())


def get_saved_courier_route_for_entities(
    entities: dict[str, str],
    *,
    task: str = "courier_route_lookup",
) -> dict[str, Any]:
    _ensure_aura_imports()
    from aura_route_queries import get_saved_courier_route  # noqa: WPS433

    courier_id = entities.get("courier_id")
    if not courier_id:
        return _missing_parameters_error(task)

    delivery_day = _resolve_delivery_day(entities)
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


def fetch_order_route(order_id: str) -> dict[str, Any] | None:
    """Load order route metadata from Aura (authorization and logistics queries)."""
    _ensure_aura_imports()
    from aura_route_queries import get_order_route  # noqa: WPS433

    return get_order_route(order_id)


def _resolve_order_route(
    order_id: str,
    *,
    prefetched_order_route: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if prefetched_order_route and str(prefetched_order_route.get("order_id")) == str(order_id):
        return prefetched_order_route
    return fetch_order_route(order_id)


def _normalize_order_ref(value: str) -> str:
    cleaned = str(value).strip().upper()
    if cleaned.startswith("ORD-"):
        return cleaned
    if re.fullmatch(r"ORD[A-Z0-9-]+", cleaned):
        return cleaned
    if re.fullmatch(r"SH[A-Z0-9-]+", cleaned):
        return cleaned
    if re.fullmatch(r"[A-Z0-9-]+", cleaned) and not cleaned.startswith("ORD"):
        return f"ORD{cleaned}"
    return cleaned


def _normalize_hub_ref(value: str) -> str:
    cleaned = str(value).strip()
    hub_match = re.search(r"hub[\s#:_-]*(\d+)", cleaned, re.I)
    if hub_match:
        return f"hub_{hub_match.group(1)}"
    return cleaned.lower().replace(" ", "_")


def _hub_field_matches(field_value: str | None, hub_ref: str) -> bool:
    if not field_value:
        return False
    return _normalize_hub_ref(str(field_value)) == hub_ref


def _find_stop_index(
    ordered_stops: list[dict[str, Any]],
    *,
    last_completed_order: str | None = None,
    current_stop: str | None = None,
) -> int | None:
    if last_completed_order:
        target = _normalize_order_ref(last_completed_order)
        for index, stop in enumerate(ordered_stops):
            order_id = _normalize_order_ref(str(stop.get("order_id", "")))
            if order_id == target:
                return index
        return None

    if current_stop:
        hub_ref = _normalize_hub_ref(current_stop)
        for index, stop in enumerate(ordered_stops):
            if _hub_field_matches(stop.get("from_hub_name"), hub_ref):
                return index
            if _hub_field_matches(stop.get("to_hub_name"), hub_ref):
                return index
            if _hub_field_matches(stop.get("order_id"), hub_ref):
                return index
        return None

    return None


def get_next_stop_for_entities(entities: dict[str, str]) -> dict[str, Any]:
    route_result = get_saved_courier_route_for_entities(
        entities,
        task="next_stop_lookup",
    )
    if not route_result.get("success"):
        answer = route_result.get("answer", "")
        if "No saved route" in answer:
            return {
                "success": False,
                "answer": "No active route was found.",
                "data": None,
            }
        return route_result

    route = route_result["data"] or {}
    stops = route.get("stops") or []
    if not stops:
        return {
            "success": False,
            "answer": "No active route was found.",
            "data": route,
        }

    last_completed_order = entities.get("last_completed_order")
    current_stop = entities.get("current_stop")
    ordered = sorted(stops, key=lambda s: s.get("sequence", 0))
    current_index = _find_stop_index(
        ordered,
        last_completed_order=last_completed_order,
        current_stop=current_stop,
    )

    if current_index is None:
        return {
            "success": False,
            "answer": "I couldn't find that stop in your assigned route.",
            "data": {"route": route},
        }

    if current_index >= len(ordered) - 1:
        return {
            "success": True,
            "answer": "You're already at the final stop on your route.",
            "data": {"next_stop": None, "route": route, "at_final_stop": True},
        }

    next_stop = ordered[current_index + 1]
    order_id = next_stop.get("order_id", "unknown")
    answer = f"Your next stop is {order_id}."
    return {"success": True, "answer": answer, "data": {"next_stop": next_stop, "route": route}}


def _extract_numeric_hub_id(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d+)$", str(value).strip())
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _normalize_logistics_entities(entities: dict[str, str]) -> dict[str, str]:
    """Normalize orchestrator entity aliases to Aura-facing fields."""
    normalized = dict(entities or {})
    if normalized.get("shipment_id") and not normalized.get("order_id"):
        # Graph routes are keyed by Order.order_id; shipment_id is treated as alias.
        normalized["order_id"] = normalized["shipment_id"]

    from_hub_id = _extract_numeric_hub_id(normalized.get("from_hub"))
    to_hub_id = _extract_numeric_hub_id(normalized.get("to_hub"))
    if from_hub_id is not None:
        normalized["from_hub_id"] = str(from_hub_id)
    if to_hub_id is not None:
        normalized["to_hub_id"] = str(to_hub_id)
    return normalized


def _missing_entity_fields_for_task(task: str) -> list[str]:
    """Flatten task entity requirement groups into a clarification field list."""
    requirements = QUERY_ENTITY_REQUIREMENTS.get(task, ())
    missing: list[str] = []
    for group in requirements:
        for entity in group:
            if entity not in missing:
                missing.append(entity)
    return missing


def _missing_parameters_error(
    task: str,
    *,
    missing_fields: list[str] | None = None,
) -> dict[str, Any]:
    fields = missing_fields if missing_fields is not None else _missing_entity_fields_for_task(task)
    return {
        "success": False,
        "error_code": "MISSING_REQUIRED_PARAMETERS",
        "missing_fields": fields,
        "answer": f"Missing required parameters for {task}.",
        "data": None,
    }


def query_logistics(
    *,
    user_query: str,
    task: str,
    entities: dict[str, str],
    prefetched_order_route: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Execute a logistics retrieval against Aura GraphDB based on task and entities."""
    _ensure_aura_imports()
    _register_graph_observer()

    resolved_trace_id = trace_id or get_current_trace_id()
    graph_prompt = (
        f"Task: {task}\nQuestion: {user_query}\nEntities: {json.dumps(entities, default=str)}"
    )
    capture_prompt(resolved_trace_id or "unknown", "graphrag_prompt", graph_prompt)
    trace_graph_request(
        {
            "question": user_query,
            "task": task,
            "entities": entities,
        },
        trace_id=resolved_trace_id,
    )

    result = _dispatch_logistics_query(
        user_query=user_query,
        task=task,
        entities=entities,
        prefetched_order_route=prefetched_order_route,
    )
    trace_graph_result(
        summarize_graph_records(result.get("data")),
        trace_id=resolved_trace_id,
    )
    return result


def _dispatch_logistics_query(
    *,
    user_query: str,
    task: str,
    entities: dict[str, str],
    prefetched_order_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from aura_route_queries import (  # noqa: WPS433
        get_route_between_hubs,
        get_orders_for_courier,
    )
    resolved_entities = _normalize_logistics_entities(entities)

    if task not in {"city_lookup", "inventory_nlsql"}:
        completeness = QueryCompletenessChecker.check(task, resolved_entities)
        if not completeness.complete:
            return _missing_parameters_error(
                task,
                missing_fields=completeness.missing_entities,
            )

    try:
        if task == "city_lookup":
            return list_cities()

        if task == "hub_lookup":
            return list_hubs(resolved_entities.get("city_name"))

        if task == "courier_route_lookup":
            return get_saved_courier_route_for_entities(
                resolved_entities,
                task="courier_route_lookup",
            )

        if task == "next_stop_lookup":
            return get_next_stop_for_entities(resolved_entities)

        if task == "route_lookup":
            order_id = resolved_entities.get("order_id")
            if order_id:
                route = _resolve_order_route(
                    order_id,
                    prefetched_order_route=prefetched_order_route,
                )
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
            from_hub_id = resolved_entities.get("from_hub_id")
            to_hub_id = resolved_entities.get("to_hub_id")
            if from_hub_id and to_hub_id:
                route = get_route_between_hubs(int(from_hub_id), int(to_hub_id))
                if route:
                    answer = (
                        f"Route from {route.get('from_hub_name')} to {route.get('to_hub_name')} "
                        f"is {route.get('map_distance_km')} km "
                        f"(ETA {route.get('estimated_time_min')} min)."
                    )
                    return {"success": True, "answer": answer, "data": route}
                return {
                    "success": False,
                    "answer": f"No route found from hub {from_hub_id} to hub {to_hub_id}.",
                    "data": None,
                }

            courier_id = resolved_entities.get("courier_id")
            if courier_id:
                return get_saved_courier_route_for_entities(
                    resolved_entities,
                    task="route_lookup",
                )
            return _missing_parameters_error("route_lookup")

        if task == "eta_lookup":
            order_id = resolved_entities.get("order_id")
            if order_id:
                route = _resolve_order_route(
                    order_id,
                    prefetched_order_route=prefetched_order_route,
                )
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
            if resolved_entities.get("courier_id"):
                route_result = get_saved_courier_route_for_entities(
                    resolved_entities,
                    task="eta_lookup",
                )
                if route_result.get("success"):
                    data = route_result["data"]
                    answer = f"Courier route ETA is {data.get('total_eta_minutes')} minutes."
                    return {"success": True, "answer": answer, "data": data}
                return route_result
            return _missing_parameters_error("eta_lookup")

        if task == "courier_lookup":
            courier_id = resolved_entities.get("courier_id")
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
            return _missing_parameters_error("courier_lookup")

        if task == "shipment_lookup":
            order_id = resolved_entities.get("order_id")
            if order_id:
                route = _resolve_order_route(
                    order_id,
                    prefetched_order_route=prefetched_order_route,
                )
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

            courier_id = resolved_entities.get("courier_id")
            if courier_id:
                orders = get_orders_for_courier(courier_id, limit=10)
                return {
                    "success": True,
                    "answer": f"Found {len(orders)} orders for courier {courier_id}.",
                    "data": orders,
                }

            return _missing_parameters_error("shipment_lookup")

        return _missing_parameters_error(task)

    except Exception as exc:
        logger.exception("Aura logistics query failed")
        return {
            "success": False,
            "answer": f"Logistics lookup failed: {exc}",
            "data": None,
            "error": str(exc),
        }
