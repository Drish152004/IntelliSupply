"""Hub and city lookup queries for logistics UI dropdowns."""

from __future__ import annotations

from aura_graphdb.aura_connection import AuraConnection


def list_cities() -> list[dict]:
    """Return all cities that have at least one hub in Aura."""
    conn = AuraConnection()
    query = """
    MATCH (h:Hub)-[:LOCATED_IN]->(c:City)
    WITH DISTINCT c
    RETURN c.city_id AS city_id, c.city_name AS city_name
    ORDER BY c.city_name
    """
    try:
        rows = conn.execute_query(query)
        return [dict(row) for row in (rows or [])]
    finally:
        conn.close()


def list_hubs(city_name: str | None = None) -> list[dict]:
    """Return hubs, optionally filtered to a single city."""
    conn = AuraConnection()
    if city_name:
        query = """
        MATCH (h:Hub)-[:LOCATED_IN]->(c:City {city_name: $city_name})
        RETURN
            h.hub_id AS hub_id,
            coalesce(h.name, h.hub_name) AS hub_name,
            c.city_name AS city_name
        ORDER BY h.hub_id
        """
        params: dict = {"city_name": city_name.strip()}
    else:
        query = """
        MATCH (h:Hub)-[:LOCATED_IN]->(c:City)
        RETURN
            h.hub_id AS hub_id,
            coalesce(h.name, h.hub_name) AS hub_name,
            c.city_name AS city_name
        ORDER BY c.city_name, h.hub_id
        """
        params = {}

    try:
        rows = conn.execute_query(query, params)
        return [dict(row) for row in (rows or [])]
    finally:
        conn.close()
