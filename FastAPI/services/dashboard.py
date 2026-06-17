"""Dashboard summary aggregation service."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from aura_graphdb.aura_auth import list_all_users
from aura_graphdb.aura_courier import list_active_couriers, list_couriers_with_orders
from aura_graphdb.aura_route_queries import get_recent_order_routes, list_delivery_days_with_orders

from services import inventory as inventory_svc

_AT_RISK_WINDOW_MINUTES = 60


def _parse_receipt_datetime(delivery_day: str | None, receipt_time: Any) -> datetime | None:
    if not delivery_day or receipt_time is None or receipt_time == "":
        return None
    day = str(delivery_day).strip()
    raw = str(receipt_time).strip()
    if not day or not raw:
        return None
    if " " in raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00").split("+")[0])
        except ValueError:
            pass
    time_part = raw[:8] if len(raw) >= 8 else raw
    try:
        return datetime.fromisoformat(f"{day}T{time_part}")
    except ValueError:
        return None


def _is_at_risk(shipment: dict[str, Any], reference_day: str, now: datetime) -> bool:
    if not shipment.get("assigned_courier_id"):
        return True
    if str(shipment.get("delivery_day") or "") != reference_day:
        return False
    due_at = _parse_receipt_datetime(shipment.get("delivery_day"), shipment.get("receipt_time"))
    if due_at is None:
        return False
    if now < due_at <= now + timedelta(minutes=_AT_RISK_WINDOW_MINUTES):
        return True
    return False


def _courier_assignment_pct(shipments: list[dict[str, Any]]) -> float:
    if not shipments:
        return 0.0
    assigned = sum(1 for row in shipments if row.get("assigned_courier_id"))
    return round(assigned / len(shipments) * 100, 1)


def _hub_coverage(shipments: list[dict[str, Any]]) -> int:
    hubs: set[str] = set()
    for row in shipments:
        for key in ("from_hub_name", "to_hub_name"):
            name = row.get(key)
            if name:
                hubs.add(str(name))
    return len(hubs)


def _unassigned_count(shipments: list[dict[str, Any]]) -> int:
    return sum(1 for row in shipments if not row.get("assigned_courier_id"))


def _top_lane(shipments: list[dict[str, Any]]) -> str | None:
    lanes: Counter[str] = Counter()
    for row in shipments:
        origin = row.get("from_hub_name")
        dest = row.get("to_hub_name")
        if origin and dest:
            lanes[f"{origin} → {dest}"] += 1
    if not lanes:
        return None
    return lanes.most_common(1)[0][0]


def _build_callouts(shipments: list[dict[str, Any]], reference_day: str) -> list[dict[str, str]]:
    now = datetime.now()
    unassigned = _unassigned_count(shipments)
    due_soon = sum(
        1
        for row in shipments
        if row.get("assigned_courier_id")
        and str(row.get("delivery_day") or "") == reference_day
        and (due := _parse_receipt_datetime(row.get("delivery_day"), row.get("receipt_time"))) is not None
        and now < due <= now + timedelta(minutes=_AT_RISK_WINDOW_MINUTES)
    )
    callouts: list[dict[str, str]] = []
    if unassigned:
        callouts.append(
            {
                "title": f"{unassigned} shipment{'s' if unassigned != 1 else ''} unassigned",
                "detail": "Assign couriers to keep routes on schedule.",
                "severity": "warning",
            }
        )
    if due_soon:
        callouts.append(
            {
                "title": f"{due_soon} shipment{'s' if due_soon != 1 else ''} due within the hour",
                "detail": "Receipt window is approaching for today’s dispatches.",
                "severity": "warning",
            }
        )
    top_lane = _top_lane(shipments)
    if top_lane:
        callouts.append(
            {
                "title": f"Busiest lane: {top_lane}",
                "detail": f"Most shipments on {reference_day}.",
                "severity": "info",
            }
        )
    if not callouts:
        callouts.append(
            {
                "title": "No operational alerts",
                "detail": f"All tracked shipments for {reference_day} look stable.",
                "severity": "info",
            }
        )
    return callouts


def get_logistics_kpis(delivery_day: str | None = None) -> dict[str, Any]:
    """Operational KPIs for the logistics dashboard (optionally scoped to a delivery day)."""
    day = delivery_day or date.today().isoformat()
    shipments: list[dict[str, Any]] = []
    couriers: list[dict[str, Any]] = []

    try:
        shipments = get_recent_order_routes(limit=500, delivery_day=day)
    except Exception:
        shipments = []

    try:
        couriers = list_couriers_with_orders(delivery_day=day)
    except Exception:
        couriers = []

    now = datetime.now()
    at_risk = sum(1 for row in shipments if _is_at_risk(row, day, now))
    unassigned = _unassigned_count(shipments)

    return {
        "delivery_day": day,
        "active_shipments": len(shipments),
        "at_risk_shipments": at_risk,
        "active_couriers": len(couriers),
        "hub_coverage": _hub_coverage(shipments),
        "unassigned_shipments": unassigned,
        "courier_assignment_pct": _courier_assignment_pct(shipments),
        "callouts": _build_callouts(shipments, day),
    }


def get_dashboard_summary() -> dict[str, Any]:
    """Admin overview metrics aggregated from live operational data."""
    shipments: list[dict[str, Any]] = []
    delivery_days: list[str] = []
    users: list[dict[str, Any]] = []
    active_couriers: list[dict[str, Any]] = []

    try:
        shipments = get_recent_order_routes(limit=200)
    except Exception:
        shipments = []

    try:
        delivery_days = list_delivery_days_with_orders(limit=30)
    except Exception:
        delivery_days = []

    try:
        users = list_all_users(limit=500)
    except Exception:
        users = []

    try:
        active_couriers = list_active_couriers(limit=1000)
    except Exception:
        active_couriers = []

    inventory_summary = None
    if inventory_svc.inventory_db_available():
        try:
            inventory_summary = inventory_svc.get_summary()
        except Exception:
            inventory_summary = None

    today = date.today().isoformat()
    reference_day = today if today in delivery_days else (delivery_days[0] if delivery_days else today)
    logistics = get_logistics_kpis(reference_day)

    role_counts: Counter[str] = Counter()
    for user in users:
        role = str(user.get("role") or "unknown").strip() or "unknown"
        role_counts[role] += 1
    # Count active courier accounts from the unified user directory
    # (profiles + Aura couriers), so admin KPI reflects full account view.
    active_courier_accounts = sum(
        1
        for user in users
        if "courier" in str(user.get("role") or "").strip().lower()
        and bool(user.get("is_active", True))
    )
    if active_courier_accounts == 0:
        # Fallback to Aura-only courier nodes if user directory is unavailable.
        active_courier_accounts = len(active_couriers)

    return {
        "recent_shipments": len(shipments),
        "courier_assignment_pct": _courier_assignment_pct(shipments),
        "active_couriers": active_courier_accounts,
        "total_accounts": len(users),
        "unassigned_shipments": _unassigned_count(shipments),
        "hub_count": _hub_coverage(shipments),
        "reference_delivery_day": reference_day,
        "inventory_summary": inventory_summary,
        "role_distribution": [
            {"role": role, "count": count}
            for role, count in role_counts.most_common()
        ],
        "logistics": logistics,
    }
