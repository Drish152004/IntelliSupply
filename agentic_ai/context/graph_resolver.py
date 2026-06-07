"""Deterministic Aura lookups to enrich ML payloads from the knowledge graph."""

from __future__ import annotations

import logging
from typing import Any

from graph_retrieval.graph_service import GraphService, get_graph_service

logger = logging.getLogger(__name__)

_ORDER_BY_ID_CYPHER = """
MATCH (o:Order)
WHERE o.order_id = $order_id OR o.shipment_id = $order_id
OPTIONAL MATCH (o)-[:FROM_HUB]->(from_hub:Hub)
OPTIONAL MATCH (o)-[:TO_HUB]->(to_hub:Hub)
OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(c:Courier)
RETURN
    o.order_id AS order_id,
    o.lat_wgs84 AS lat_wgs84,
    o.lon_wgs84 AS lon_wgs84,
    o.receipt_lat_wgs84 AS receipt_lat_wgs84,
    o.receipt_lon_wgs84 AS receipt_lon_wgs84,
    o.city_name AS city_name,
    o.ds AS ds,
    o.delivery_day AS delivery_day,
    o.receipt_time AS receipt_time,
    o.typecode AS typecode,
    o.aoi_id AS aoi_id,
    c.courier_id AS delivery_user_id,
    from_hub.rep_dipan_id AS from_dipan_id,
    from_hub.latitude AS receipt_lat,
    from_hub.longitude AS receipt_lng,
    to_hub.latitude AS poi_lat,
    to_hub.longitude AS poi_lng
LIMIT 1
""".strip()

_ORDER_BY_HUBS_CYPHER = """
MATCH (from_hub:Hub)<-[:FROM_HUB]-(o:Order)-[:TO_HUB]->(to_hub:Hub)
WHERE toLower(from_hub.name) = toLower($from_hub)
  AND toLower(to_hub.name) = toLower($to_hub)
OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(c:Courier)
RETURN
    o.order_id AS order_id,
    o.lat_wgs84 AS lat_wgs84,
    o.lon_wgs84 AS lon_wgs84,
    o.receipt_lat_wgs84 AS receipt_lat_wgs84,
    o.receipt_lon_wgs84 AS receipt_lon_wgs84,
    o.city_name AS city_name,
    o.ds AS ds,
    o.delivery_day AS delivery_day,
    o.receipt_time AS receipt_time,
    o.typecode AS typecode,
    o.aoi_id AS aoi_id,
    c.courier_id AS delivery_user_id,
    from_hub.rep_dipan_id AS from_dipan_id,
    from_hub.latitude AS receipt_lat,
    from_hub.longitude AS receipt_lng,
    to_hub.latitude AS poi_lat,
    to_hub.longitude AS poi_lng
ORDER BY o.updated_at DESC
LIMIT 1
""".strip()


def _coerce_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize Neo4j record values for payload building."""
    cleaned: dict[str, Any] = {}
    for key, value in record.items():
        if value is None:
            continue
        if hasattr(value, "isoformat"):
            cleaned[key] = value.isoformat()
        else:
            cleaned[key] = value
    return cleaned


class GraphResolver:
    """Retrieve graph-enrichable fields via direct Aura lookups."""

    def __init__(self, graph_service: GraphService | None = None) -> None:
        self._graph_service = graph_service or get_graph_service()

    def resolve(self, task: str, entities: dict[str, str]) -> dict[str, Any]:
        """Return graph-enriched field values for the given task and entities."""
        if task == "demand_forecast":
            return {}

        order_id = entities.get("order_id") or entities.get("shipment_id")
        if order_id:
            return self._lookup_order(order_id)

        from_hub = entities.get("from_hub")
        to_hub = entities.get("to_hub")
        if from_hub and to_hub:
            return self._lookup_order_by_hubs(from_hub, to_hub)

        return {}

    def _lookup_order(self, order_id: str) -> dict[str, Any]:
        records = self._graph_service.execute(
            _ORDER_BY_ID_CYPHER,
            {"order_id": order_id},
        )
        if not records:
            logger.info("Graph enrichment: no order found for order_id=%s", order_id)
            return {}
        return _coerce_record(records[0])

    def _lookup_order_by_hubs(self, from_hub: str, to_hub: str) -> dict[str, Any]:
        records = self._graph_service.execute(
            _ORDER_BY_HUBS_CYPHER,
            {"from_hub": from_hub, "to_hub": to_hub},
        )
        if not records:
            logger.info(
                "Graph enrichment: no order found for from_hub=%s to_hub=%s",
                from_hub,
                to_hub,
            )
            return {}
        return _coerce_record(records[0])


_resolver: GraphResolver | None = None


def get_graph_resolver() -> GraphResolver:
    global _resolver
    if _resolver is None:
        _resolver = GraphResolver()
    return _resolver


def reset_graph_resolver(resolver: GraphResolver | None = None) -> None:
    global _resolver
    _resolver = resolver if resolver is not None else GraphResolver()
