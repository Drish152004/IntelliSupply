"""Map natural-language queries to ML inference tasks within a domain."""

from __future__ import annotations

LOGISTICS_ETA_KEYWORDS = ("eta", "arrival", "minutes", "delivery time", "how long")
LOGISTICS_NEXT_STOP_KEYWORDS = ("next stop", "next-stop")
LOGISTICS_ROUTE_KEYWORDS = ("route", "sequence", "optimize", "ordering", "visit order")


def logistics_task(query: str) -> str:
    """Return one of: eta, next_stop, route."""
    q = query.lower()
    if any(keyword in q for keyword in LOGISTICS_ETA_KEYWORDS):
        return "eta"
    if any(keyword in q for keyword in LOGISTICS_NEXT_STOP_KEYWORDS):
        return "next_stop"
    if any(keyword in q for keyword in LOGISTICS_ROUTE_KEYWORDS):
        return "route"
    return "route"

