"""Generate human-readable answers from raw Aura GraphDB results.

This module is the answer-generation layer. Aura Bridge stays a pure
data-access layer; it returns raw GraphDB JSON only. Here we decide what to
show to the user based on the original ``user_query``, the resolved ``task``,
and the raw ``graph_result`` data.
"""

from __future__ import annotations

import re
from typing import Any

_LOCATION_WORDS: tuple[str, ...] = ("city", "location", "located", "where")
_COURIER_WORDS: tuple[str, ...] = (
    "courier",
    "assigned",
    "handling",
    "handle",
    "handles",
    "who",
    "driver",
)
_ROUTE_WORDS: tuple[str, ...] = ("route", "path", "hub", "hubs")
_DELIVERY_DAY_WORDS: tuple[str, ...] = (
    "delivery day",
    "delivery date",
    "deliver day",
    "deliver date",
    "scheduled",
    "schedule",
    "which day",
    "what day",
    "when",
    "day",
    "date",
)
_NEXT_STOP_WORDS: tuple[str, ...] = ("next stop", "next", "upcoming", "first stop")
_REMAINING_WORDS: tuple[str, ...] = ("remaining", "left", "rest", "pending")
_ETA_WORDS: tuple[str, ...] = (
    "eta",
    "how long",
    "take",
    "duration",
    "travel time",
    "arrival",
    "arrive",
    "finish",
    "complete",
)
_ETA_ARRIVAL_WORDS: tuple[str, ...] = ("finish", "arrive", "arrival", "when")
_ETA_DURATION_WORDS: tuple[str, ...] = ("how long", "take", "duration", "travel time")
_COUNT_WORDS: tuple[str, ...] = ("how many", "count", "number of", "total")
_LIST_WORDS: tuple[str, ...] = ("which", "list", "show", "what orders", "what are")


def synthesize_answer(user_query: str, task: str, graph_result: Any) -> str:
    """Build a concise, human-readable answer from raw graph data.

    ``graph_result`` is the raw ``data`` payload returned by Aura Bridge
    (i.e. ``aura_response["data"]``). No GraphDB calls happen here.
    """
    query = (user_query or "").lower()

    if graph_result in (None, [], {}, ""):
        return "No matching records were found."

    if task == "order_lookup":
        return _synthesize_order_lookup(query, graph_result)
    if task == "courier_route":
        return _synthesize_courier_route(query, graph_result)
    if task == "courier_orders":
        return _synthesize_courier_orders(query, graph_result)
    if task == "recent_routes":
        return _synthesize_recent_routes(graph_result)
    if task == "delivery_days":
        return _synthesize_delivery_days(graph_result)
    if task == "hub_route":
        return _synthesize_hub_route(graph_result)
    if task == "dynamic_graph_query":
        return _synthesize_dynamic(graph_result)

    return _synthesize_generic(graph_result)


def _contains(text: str, keywords: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in keywords)


def _synthesize_order_lookup(query: str, route: Any) -> str:
    if not isinstance(route, dict):
        return _synthesize_generic(route)

    order_id = route.get("order_id")

    if _contains(query, _DELIVERY_DAY_WORDS) and route.get("delivery_day"):
        return (
            f"Order {order_id} is scheduled for delivery on {route['delivery_day']}."
        )

    if _contains(query, _LOCATION_WORDS) and route.get("city_name"):
        return f"Order {order_id} is in {route['city_name']}."

    if _contains(query, _COURIER_WORDS) and route.get("assigned_courier_name"):
        return f"{route['assigned_courier_name']} is handling order {order_id}."

    if _contains(query, _ROUTE_WORDS) and (
        route.get("from_hub_name") or route.get("to_hub_name")
    ):
        return f"Route: {route.get('from_hub_name')} → {route.get('to_hub_name')}."

    return _summarize_order(route)


def _summarize_order(route: dict[str, Any]) -> str:
    order_id = route.get("order_id")
    parts: list[str] = []
    if route.get("city_name"):
        parts.append(f"city {route['city_name']}")
    if route.get("assigned_courier_name"):
        parts.append(f"courier {route['assigned_courier_name']}")
    if route.get("from_hub_name") and route.get("to_hub_name"):
        parts.append(f"route {route['from_hub_name']} → {route['to_hub_name']}")
    if parts:
        return f"Order {order_id}: " + ", ".join(parts) + "."
    return f"Order {order_id} found."


def _synthesize_courier_route(query: str, route: Any) -> str:
    if not isinstance(route, dict):
        return _synthesize_generic(route)

    courier = route.get("courier_name") or route.get("courier_id") or "the courier"
    delivery_day = route.get("delivery_day")
    stops = route.get("stops") or []
    sequence = route.get("predicted_sequence") or [
        stop.get("order_id") for stop in stops if stop.get("order_id")
    ]

    if _contains(query, _ETA_WORDS):
        return _synthesize_courier_eta(query, route, courier, stops)

    if _contains(query, _NEXT_STOP_WORDS):
        if sequence:
            return f"Next stop for {courier} is order {sequence[0]}."
        return f"No upcoming stops found for {courier}."

    if _contains(query, _REMAINING_WORDS):
        if len(sequence) > 1:
            remaining = ", ".join(str(order_id) for order_id in sequence[1:])
            return (
                f"{len(sequence) - 1} remaining stops for {courier}: {remaining}."
            )
        return f"No remaining stops for {courier}."

    if sequence:
        path = " → ".join(str(order_id) for order_id in sequence)
        suffix = f" on {delivery_day}" if delivery_day else ""
        return f"Route for {courier}{suffix}: {path}."

    return f"No route found for {courier}."


def _synthesize_courier_eta(
    query: str,
    route: dict[str, Any],
    courier: str,
    stops: list[Any],
) -> str:
    """Answer ETA / travel-time / arrival questions for a courier route."""
    eta_value = route.get("predicted_eta_min")
    if eta_value is None:
        eta_value = route.get("total_eta_minutes")
    last_stop = stops[-1] if stops and isinstance(stops[-1], dict) else {}
    if eta_value is None:
        eta_value = last_stop.get("eta_from_start_minutes")
    estimated_arrival = last_stop.get("estimated_arrival")

    if _contains(query, _ETA_ARRIVAL_WORDS) and estimated_arrival:
        return f"{courier} is expected to finish around {estimated_arrival}."

    if eta_value is None:
        if estimated_arrival:
            return f"{courier} is expected to finish around {estimated_arrival}."
        return f"No ETA information is available for {courier}."

    minutes = int(round(float(eta_value)))
    if _contains(query, _ETA_DURATION_WORDS):
        return (
            f"{courier}'s route is expected to take approximately {minutes} minutes."
        )
    return (
        f"{courier} is expected to complete the route in approximately "
        f"{minutes} minutes."
    )


def _synthesize_courier_orders(query: str, orders: Any) -> str:
    if not isinstance(orders, list):
        return _synthesize_generic(orders)

    count = len(orders)
    if not count:
        return "No orders were found for this courier."

    order_ids = [str(order.get("order_id")) for order in orders if order.get("order_id")]

    if _contains(query, _COUNT_WORDS):
        return f"There are {count} orders."

    if _contains(query, _LIST_WORDS):
        listed = ", ".join(order_ids)
        return f"Orders ({count}): {listed}." if listed else f"There are {count} orders."

    listed = ", ".join(order_ids[:10])
    if listed:
        suffix = "" if count <= 10 else f" (showing first 10 of {count})"
        return f"{count} orders: {listed}{suffix}."
    return f"There are {count} orders."


def _synthesize_recent_routes(routes: Any) -> str:
    if not isinstance(routes, list):
        return _synthesize_generic(routes)

    count = len(routes)
    if not count:
        return "No recent routes were found."

    samples: list[str] = []
    for route in routes[:5]:
        if not isinstance(route, dict):
            continue
        order_id = route.get("order_id")
        from_hub = route.get("from_hub_name")
        to_hub = route.get("to_hub_name")
        if order_id and from_hub and to_hub:
            samples.append(f"{order_id} ({from_hub} → {to_hub})")
        elif order_id:
            samples.append(str(order_id))

    detail = "; ".join(samples)
    if detail:
        return f"{count} recent routes: {detail}."
    return f"{count} recent routes found."


def _synthesize_delivery_days(days: Any) -> str:
    if not isinstance(days, list) or not days:
        return "No delivery days with orders were found."
    listed = ", ".join(str(day) for day in days)
    return f"Available delivery days: {listed}."


def _synthesize_hub_route(data: Any) -> str:
    if not isinstance(data, dict):
        return _synthesize_generic(data)

    distance = data.get("distance") or {}
    from_name = distance.get("from_hub_name")
    to_name = distance.get("to_hub_name")
    distance_km = distance.get("map_distance_km")
    eta_min = distance.get("estimated_time_min")

    if from_name and to_name and distance_km is not None:
        return f"Route from {from_name} to {to_name} is {distance_km} km (ETA {eta_min} min)."
    if from_name and to_name:
        return f"Route: {from_name} → {to_name}."
    return "Route hubs resolved."


def _synthesize_dynamic(data: Any) -> str:
    """Render dynamic GraphDB rows. Handles single-row aggregations and lists.

    Dynamic queries return arbitrary projected rows (counts, aggregations,
    rankings, lists), so this favors readability over task-specific shaping.
    """
    rows = data if isinstance(data, list) else ([data] if data else [])
    if not rows:
        return "No matching records were found."

    # Single-row result (typical for counts/aggregations): state each field.
    if len(rows) == 1 and isinstance(rows[0], dict) and rows[0]:
        pairs = [f"{str(key).replace('_', ' ')}: {value}" for key, value in rows[0].items()]
        return "; ".join(pairs) + "."

    samples: list[str] = []
    for row in rows[:5]:
        if isinstance(row, dict) and row:
            samples.append(", ".join(f"{key}={value}" for key, value in list(row.items())[:3]))
    detail = "; ".join(sample for sample in samples if sample)
    if detail:
        suffix = "" if len(rows) <= 5 else f" (showing first 5 of {len(rows)})"
        return f"{len(rows)} results: {detail}{suffix}."
    return f"{len(rows)} results found."


def _synthesize_generic(data: Any) -> str:
    if isinstance(data, list):
        return f"{len(data)} records found." if data else "No matching records were found."
    if isinstance(data, dict):
        for key in ("order_id", "name", "courier_name", "id"):
            if data.get(key):
                return f"Found {key.replace('_', ' ')} {data[key]}."
        return "Record found."
    if data:
        return str(data)
    return "No matching records were found."
