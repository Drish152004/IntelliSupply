"""Courier graph operations in Neo4j Aura."""

from __future__ import annotations
import uuid
from typing import Any
from aura_graphdb.aura_connection import AuraConnection
from rag.supabase.supabase_notifications import create_notification

COURIER_ROLE_ID = 2
COURIER_ROLE_NAME = "courier"

def _safe_create_notification(**kwargs):
    try:
        create_notification(**kwargs)
    except Exception as exc:
        print(f"Notification create failed: {exc}")

def get_courier_by_email(email: str) -> dict[str, Any] | None:
    """Fetch a Courier node from Aura using email."""
    conn = AuraConnection()
    query = """
    MATCH (c:Courier {email: toLower(trim($email))})
    OPTIONAL MATCH (c)-[:HAS_ROLE]->(r:Role)
    OPTIONAL MATCH (c)-[:OPERATES_IN]->(city:City)
    OPTIONAL MATCH (c)-[:ASSIGNED_TO_HUB]->(hub:Hub)
    OPTIONAL MATCH (c)-[:LINKED_TO_PROFILE]->(p:Profile)

    RETURN
        c.courier_id AS courier_id,
        c.profile_id AS profile_id,
        p.id AS linked_profile_id,
        c.name AS name,
        c.email AS email,
        c.ds AS ds,
        c.start_lat_wgs84 AS start_lat_wgs84,
        c.start_lon_wgs84 AS start_lon_wgs84,
        coalesce(city.city_id, c.city_id) AS city_id,
        coalesce(city.city_name, c.city_name) AS city_name,
        coalesce(hub.hub_id, c.hub_id) AS hub_id,
        coalesce(hub.name, c.hub_name) AS hub_name,
        r.role_id AS role_id,
        r.role_name AS role,
        c.is_active AS is_active
    LIMIT 1
    """
    try:
        result = conn.execute_query(query, {"email": email.lower().strip()})
        return result[0] if result else None
    finally:
        conn.close()

def create_courier_node(
    *,
    name: str,
    email: str,
    city_name: str,
    hub_name: str,
    profile_id: str | None = None,
    courier_id: str | None = None,
    ds: int = 318,
) -> dict[str, Any]:
    """Create an operational Courier node in Aura."""
    existing = get_courier_by_email(email)

    if existing:
        return {
            "success": False,
            "message": "Courier with this email already exists in Aura.",
            "courier": existing,
        }

    courier_id = courier_id or uuid.uuid4().hex
    conn = AuraConnection()
    query = """
    MATCH (hub:Hub {name: $hub_name})-[:LOCATED_IN]->(city:City {city_name: $city_name})

    MERGE (role:Role {role_id: toInteger($role_id)})
    ON CREATE SET
        role.created_at = datetime()
    SET
        role.role_name = $role_name,
        role.updated_at = datetime()

    MERGE (courier:Courier {courier_id: $courier_id})
    ON CREATE SET
        courier.created_at = datetime()
    SET
        courier.profile_id = $profile_id,
        courier.name = $name,
        courier.email = toLower(trim($email)),
        courier.city_id = city.city_id,
        courier.city_name = city.city_name,
        courier.hub_id = hub.hub_id,
        courier.hub_name = hub.name,
        courier.ds = toInteger($ds),
        courier.start_lat_wgs84 = hub.latitude,
        courier.start_lon_wgs84 = hub.longitude,
        courier.is_active = true,
        courier.updated_at = datetime()

    MERGE (courier)-[:HAS_ROLE]->(role)
    MERGE (courier)-[:OPERATES_IN]->(city)
    MERGE (courier)-[:ASSIGNED_TO_HUB]->(hub)

    WITH courier, role, city, hub
    OPTIONAL MATCH (profile:Profile {id: $profile_id})
    FOREACH (_ IN CASE WHEN profile IS NULL THEN [] ELSE [1] END |
        MERGE (courier)-[:LINKED_TO_PROFILE]->(profile)
    )

    RETURN
        courier.courier_id AS courier_id,
        courier.profile_id AS profile_id,
        courier.name AS name,
        courier.email AS email,
        city.city_id AS city_id,
        city.city_name AS city_name,
        hub.hub_id AS hub_id,
        hub.name AS hub_name,
        courier.ds AS ds,
        courier.start_lat_wgs84 AS start_lat_wgs84,
        courier.start_lon_wgs84 AS start_lon_wgs84,
        role.role_id AS role_id,
        role.role_name AS role,
        courier.is_active AS is_active
    """

    try:
        result = conn.execute_write(
            query,
            {
                "courier_id": courier_id,
                "profile_id": str(profile_id) if profile_id else None,
                "name": name.strip(),
                "email": email.lower().strip(),
                "city_name": city_name.strip(),
                "hub_name": hub_name.strip(),
                "ds": int(ds),
                "role_id": COURIER_ROLE_ID,
                "role_name": COURIER_ROLE_NAME,
            },
        )

        if not result:
            return {
                "success": False,
                "message": "Hub and city combination not found in Aura. Seed hubs/cities first.",
            }

        courier = result[0]

        for role in ["admin", "logistics_manager"]:
            _safe_create_notification(
                title="New courier created",
                message=f"Courier {courier['name']} was assigned to {courier['hub_name']} in {courier['city_name']}.",
                alert_type="courier_created",
                severity="medium",
                target_role=role,
                related_entity_type="courier",
                related_entity_id=courier["courier_id"],
                source="graphdb",
            )

        return {
            "success": True,
            "message": "Courier node created successfully.",
            "courier": courier,
        }
    finally:
        conn.close()

def deactivate_courier(courier_id: str) -> dict[str, Any]:
    """Mark a courier inactive instead of deleting the node."""
    conn = AuraConnection()
    query = """
    MATCH (courier:Courier {courier_id: $courier_id})
    SET
        courier.is_active = false,
        courier.updated_at = datetime()
    RETURN
        courier.courier_id AS courier_id,
        courier.name AS name,
        courier.email AS email,
        courier.is_active AS is_active
    """

    try:
        result = conn.execute_write(query, {"courier_id": courier_id})

        if not result:
            return {
                "success": False,
                "message": "Courier not found.",
            }

        courier = result[0]

        for role in ["admin", "logistics_manager"]:
            _safe_create_notification(
                title="Courier deactivated",
                message=f"Courier {courier['name']} has been marked inactive.",
                alert_type="courier_deactivated",
                severity="high",
                target_role=role,
                related_entity_type="courier",
                related_entity_id=courier["courier_id"],
                source="graphdb",
            )

        return {
            "success": True,
            "message": "Courier deactivated successfully.",
            "courier": courier,
        }
    finally:
        conn.close()