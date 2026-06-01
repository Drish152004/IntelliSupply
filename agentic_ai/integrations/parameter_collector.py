"""
Conversational one-field-at-a-time collection for ML tool payloads.
"""

from __future__ import annotations

from typing import Any, Callable

FieldSpec = tuple[str, str, Callable[[str], Any]]

ETA_FIELDS: list[FieldSpec] = [
    ("delivery_user_id", "Which courier is handling this delivery? (courier ID, number)", int),
    ("from_dipan_id", "Which hub or dipan did the shipment start from? (number)", int),
    ("aoi_id", "What is the delivery area ID for this shipment? (number)", int),
    ("receipt_time", "When was the package received? (e.g. 2024-10-12T14:30:00)", str),
    ("receipt_lat", "What is the pickup latitude?", float),
    ("receipt_lng", "What is the pickup longitude?", float),
    ("poi_lat", "What is the delivery latitude?", float),
    ("poi_lng", "What is the delivery longitude?", float),
]

NEXT_STOP_SCALAR_FIELDS: list[FieldSpec] = [
    ("current_lat", "Where is the courier right now? (latitude)", float),
    ("current_lng", "What is the courier's current longitude?", float),
    ("route_start_time", "When did this route start? (e.g. 2024-10-12T14:30:00)", str),
    (
        "stops_completed",
        "How many stops are already completed on this route? (enter 0 if none)",
        int,
    ),
]

ORDER_STOP_FIELDS: list[FieldSpec] = [
    ("order_id", "What is the order ID for this stop?", str),
    ("poi_lat", "Delivery latitude for this stop?", float),
    ("poi_lng", "Delivery longitude for this stop?", float),
    ("receipt_time", "Receipt time for this stop? (ISO datetime)", str),
    ("receipt_lat", "Pickup latitude for this stop?", float),
    ("receipt_lng", "Pickup longitude for this stop?", float),
    ("city_name", "Which city is this stop in?", str),
    ("typecode", "Type code for this stop?", str),
    ("aoi_id", "Area ID for this stop?", str),
]

DEMAND_RECORD_FIELDS: list[FieldSpec] = [
    ("city", "Which city is this demand forecast for?", str),
    ("region_id", "What is the region ID? (e.g. 56)", str),
    (
        "day_of_week",
        "What day of week is it? (0=Monday through 6=Sunday)",
        int,
    ),
    ("month", "Which month (1-12)?", int),
    ("day_of_month", "What day of the month (1-31)?", int),
    ("day_of_year", "What day of the year (1-366)?", int),
    ("is_weekend", "Is it a weekend? (0=no, 1=yes)", int),
    ("lag_1", "What was demand 1 day ago?", float),
    ("lag_2", "What was demand 2 days ago?", float),
    ("lag_7", "What was demand 7 days ago?", float),
    ("lag_14", "What was demand 14 days ago?", float),
    ("rolling_mean_7", "What is the 7-day rolling mean demand?", float),
    ("rolling_std_7", "What is the 7-day rolling standard deviation?", float),
    ("rolling_mean_28", "What is the 28-day rolling mean demand?", float),
    (
        "ds",
        "Forecast date (YYYY-MM-DD)? Type 'skip' if not needed.",
        str,
    ),
]

TOOL_FIELD_PLANS: dict[str, dict[str, Any]] = {
    "predict_demand": {"scalars": DEMAND_RECORD_FIELDS},
    "predict_eta": {"scalars": ETA_FIELDS},
    "predict_next_stop": {
        "scalars": NEXT_STOP_SCALAR_FIELDS,
        "list_key": "remaining_orders",
        "list_label": "remaining stop",
    },
    "predict_route_sequence": {
        "scalars": [],
        "list_key": "orders",
        "list_label": "route stop",
    },
}


def _field_present(partial: dict[str, Any], path: str) -> bool:
    return path in partial and partial[path] is not None


def coerce_value(raw: str, coerce: Callable[[str], Any]) -> Any:
    text = raw.strip()
    if coerce is int:
        return int(float(text))
    if coerce is float:
        return float(text)
    return text


def apply_answer(partial: dict[str, Any], path: str, raw: str, coerce: Callable[[str], Any]) -> None:
    partial[path] = coerce_value(raw, coerce)


def _list_state(partial: dict[str, Any], list_key: str) -> dict[str, Any]:
    state = partial.setdefault("_collection", {})
    return state.setdefault(
        list_key,
        {"items": [], "current": {}, "target_count": 0, "phase": "ask_count"},
    )


def next_collection_step(tool_name: str, partial: dict[str, Any]) -> tuple[str, str] | None:
    plan = TOOL_FIELD_PLANS.get(tool_name)
    if not plan:
        return None

    for path, prompt, _ in plan.get("scalars", []):
        if not _field_present(partial, path):
            return path, prompt

    list_key = plan.get("list_key")
    if not list_key:
        return None

    coll = _list_state(partial, list_key)
    label = plan.get("list_label", "stop")

    if coll["phase"] == "ask_count":
        return (
            f"{list_key}.__count__",
            f"How many {label}s should we plan for? (enter a number, at least 1)",
        )

    for path, prompt, _ in ORDER_STOP_FIELDS:
        if path not in coll["current"]:
            idx = len(coll["items"]) + 1
            return (
                f"{list_key}[{idx}].{path}",
                f"For {label} #{idx}: {prompt}",
            )

    coll["items"].append(dict(coll["current"]))
    coll["current"] = {}
    if len(coll["items"]) < coll["target_count"]:
        first_path, first_prompt, _ = ORDER_STOP_FIELDS[0]
        idx = len(coll["items"]) + 1
        return (
            f"{list_key}[{idx}].{first_path}",
            f"For {label} #{idx}: {first_prompt}",
        )

    partial[list_key] = coll["items"]
    partial.pop("_collection", None)
    return None


def parse_field_answer(
    tool_name: str,
    partial: dict[str, Any],
    field_path: str,
    raw: str,
) -> None:
    if field_path.endswith(".__count__"):
        plan = TOOL_FIELD_PLANS[tool_name]
        list_key = plan["list_key"]
        coll = _list_state(partial, list_key)
        coll["target_count"] = max(1, int(float(raw.strip())))
        coll["phase"] = "order"
        return

    if "[" in field_path:
        plan = TOOL_FIELD_PLANS[tool_name]
        list_key = plan["list_key"]
        coll = _list_state(partial, list_key)
        field_name = field_path.split(".")[-1]
        coerce = next(c for f, _, c in ORDER_STOP_FIELDS if f == field_name)
        coll["current"][field_name] = coerce_value(raw, coerce)
        return

    plan = TOOL_FIELD_PLANS[tool_name]
    for path, _, coerce in plan.get("scalars", []):
        if path == field_path:
            apply_answer(partial, path, raw, coerce)
            return

    raise ValueError(f"Unknown field path: {field_path}")


def finalize_partial(tool_name: str, partial: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in partial.items() if not k.startswith("_")}
    if tool_name == "predict_next_stop" and "stops_completed" not in out:
        out["stops_completed"] = 0
    if tool_name == "predict_demand":
        records = out.get("records")
        if isinstance(records, list) and records:
            return {"records": records}
        record = dict(out)
        ds = record.get("ds")
        if ds is None or str(ds).strip().lower() in {"", "skip", "none", "n/a"}:
            record.pop("ds", None)
        return {"records": [record]}
    return out
