import uuid
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from aura_graphdb.aura_connection import AuraConnection


COURIER_ROLE_ID = 2
COURIER_ROLE_NAME = "courier"


def get_courier_by_email(email: str):
    conn = AuraConnection()

    query = """
    MATCH (c:Courier {email: $email})
    OPTIONAL MATCH (c)-[:HAS_ROLE]->(r:Role)
    OPTIONAL MATCH (c)-[:OPERATES_IN]->(city:City)

    RETURN
        c.courier_id AS courier_id,
        c.name AS name,
        c.email AS email,
        c.password_hash AS password_hash,
        c.ds AS ds,
        c.start_lat_wgs84 AS start_lat_wgs84,
        c.start_lon_wgs84 AS start_lon_wgs84,
        coalesce(city.city_id, c.city_id) AS city_id,
        coalesce(city.city_name, c.city_name) AS city_name,
        c.hub_id AS hub_id,
        c.hub_name AS hub_name,
        r.role_id AS role_id,
        r.role_name AS role
    LIMIT 1
    """

    try:
        result = conn.execute_query(query, {
            "email": email.lower().strip()
        })

        return result[0] if result else None

    finally:
        conn.close()


def create_courier_user(
    name: str,
    email: str,
    password: str,
    city_name: str,
    hub_name: str,
    ds: int = 318
):
    existing = get_courier_by_email(email)

    if existing:
        return {
            "success": False,
            "message": "Courier with this email already exists."
        }

    courier_id = uuid.uuid4().hex
    password_hash = generate_password_hash(password)

    conn = AuraConnection()

    query = """
    MATCH (hub:Hub {name: $hub_name})-[:LOCATED_IN]->(city:City {city_name: $city_name})

    MERGE (role:Role {role_id: $role_id})
    SET role.role_name = $role_name

    CREATE (courier:Courier {
        courier_id: $courier_id,
        name: $name,
        email: $email,
        password_hash: $password_hash,
        city_id: city.city_id,
        city_name: city.city_name,
        hub_id: hub.hub_id,
        hub_name: hub.name,
        ds: toInteger($ds),
        start_lat_wgs84: hub.latitude,
        start_lon_wgs84: hub.longitude,
        is_active: true,
        created_at: datetime(),
        updated_at: datetime()
    })

    MERGE (courier)-[:HAS_ROLE]->(role)
    MERGE (courier)-[:OPERATES_IN]->(city)
    MERGE (courier)-[:ASSIGNED_TO_HUB]->(hub)

    RETURN
        courier.courier_id AS courier_id,
        courier.name AS name,
        courier.email AS email,
        courier.city_name AS city_name,
        courier.hub_name AS hub_name,
        courier.ds AS ds,
        courier.start_lat_wgs84 AS start_lat_wgs84,
        courier.start_lon_wgs84 AS start_lon_wgs84
    """

    try:
        result = conn.execute_write(query, {
            "courier_id": courier_id,
            "name": name.strip(),
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "city_name": city_name.strip(),
            "hub_name": hub_name.strip(),
            "ds": ds,
            "role_id": COURIER_ROLE_ID,
            "role_name": COURIER_ROLE_NAME
        })

        if not result:
            return {
                "success": False,
                "message": "Hub and city combination not found in Aura. Seed hubs/cities first."
            }

        return {
            "success": True,
            "message": "Courier created successfully.",
            "courier": result[0]
        }

    finally:
        conn.close()


def login_courier(email: str, password: str):
    courier = get_courier_by_email(email)

    if not courier:
        return {
            "success": False,
            "message": "Invalid email or password."
        }

    password_hash = courier.get("password_hash")

    if not password_hash or not check_password_hash(password_hash, password):
        return {
            "success": False,
            "message": "Invalid email or password."
        }

    return {
        "success": True,
        "message": "Courier login successful.",
        "courier": {
            "courier_id": courier["courier_id"],
            "name": courier["name"],
            "email": courier["email"],
            "city_id": courier["city_id"],
            "city_name": courier["city_name"],
            "hub_id": courier["hub_id"],
            "hub_name": courier["hub_name"],
            "ds": courier["ds"],
            "start_lat_wgs84": courier["start_lat_wgs84"],
            "start_lon_wgs84": courier["start_lon_wgs84"],
            "role_id": courier["role_id"],
            "role": courier["role"]
        }
    }


if __name__ == "__main__":
    print(create_courier_user(
        name="Test Courier",
        email="courier1@example.com",
        password="test123",
        city_name="Chongqing",
        hub_name="Hub_1",
        ds=318
    ))