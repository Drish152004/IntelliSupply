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


def list_hubs_with_coordinates() -> list[dict]:
    """Return all hubs with WGS84 coordinates for map display."""
    conn = AuraConnection()
    query = """
    MATCH (h:Hub)-[:LOCATED_IN]->(c:City)
    WHERE h.lat IS NOT NULL AND h.lng IS NOT NULL
    RETURN
        h.hub_id AS hub_id,
        coalesce(h.name, h.hub_name) AS hub_name,
        c.city_name AS city_name,
        h.lat AS lat,
        h.lng AS lng,
        coalesce(h.hub_type, 'hub') AS hub_type
    ORDER BY c.city_name, h.hub_id
    """
    try:
        rows = conn.execute_query(query)
        return [dict(row) for row in (rows or [])]
    finally:
        conn.close()
def resolve_hub(
    *,
    hub_id: int | str | None = None,
    hub_name: str | None = None,
) -> dict | None:
    """
    Resolve hub by hub_id or hub name.

    Examples:
    - resolve_hub(hub_id=32)
    - resolve_hub(hub_name="Hub 32")
    - resolve_hub(hub_name="hub 32")
    """
    parsed_hub_id: int | None = None

    if hub_id is not None and str(hub_id).strip():
        try:
            parsed_hub_id = int(str(hub_id).strip())
        except ValueError:
            parsed_hub_id = None

    clean_name = (hub_name or "").strip()

    # If user says "Hub 32", also try to extract 32 as hub_id.
    if parsed_hub_id is None and clean_name.lower().startswith("hub "):
        try:
            parsed_hub_id = int(clean_name.split()[-1])
        except ValueError:
            parsed_hub_id = None

    conn = AuraConnection()

    query = """
    MATCH (h:Hub)
    OPTIONAL MATCH (h)-[:LOCATED_IN]->(c:City)
    WHERE
        ($hub_id IS NOT NULL AND h.hub_id = $hub_id)
        OR (
            $hub_name <> ''
            AND toLower(coalesce(h.name, h.hub_name, '')) = toLower($hub_name)
        )
        OR (
            $hub_name <> ''
            AND toLower(coalesce(h.name, h.hub_name, '')) CONTAINS toLower($hub_name)
        )

    RETURN
        h.hub_id AS hub_id,
        coalesce(h.name, h.hub_name) AS hub_name,
        c.city_id AS city_id,
        c.city_name AS city_name,
        h.lat AS lat,
        h.lng AS lng,
        h.poi_lat AS poi_lat,
        h.poi_lng AS poi_lng,
        coalesce(h.hub_type, 'hub') AS hub_type
    ORDER BY
        CASE
            WHEN $hub_id IS NOT NULL AND h.hub_id = $hub_id THEN 0
            WHEN $hub_name <> '' AND toLower(coalesce(h.name, h.hub_name, '')) = toLower($hub_name) THEN 1
            ELSE 2
        END,
        h.hub_id
    LIMIT 1
    """

    try:
        rows = conn.execute_query(
            query,
            {
                "hub_id": parsed_hub_id,
                "hub_name": clean_name,
            },
        )
        return dict(rows[0]) if rows else None
    finally:
        conn.close()