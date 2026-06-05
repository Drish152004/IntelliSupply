import uuid
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from aura_graphdb.aura_connection import AuraConnection


ROLE_MAP = {
    "admin": 1,
    "courier": 2,
    "inventory_manager": 3,
    "logistics_manager": 4
}

ALLOWED_ROLES = set(ROLE_MAP.keys())


def normalize_role(role_name: Optional[str]) -> str:
    if not role_name:
        return "courier"

    role_name = role_name.strip().lower()

    if role_name not in ALLOWED_ROLES:
        return "courier"

    return role_name


def get_role_id(role_name: str) -> int:
    role_name = normalize_role(role_name)
    return ROLE_MAP[role_name]


def count_profiles() -> int:
    conn = AuraConnection()

    query = """
    MATCH (p:Profile)
    RETURN count(p) AS profile_count
    """

    try:
        result = conn.execute_query(query)
        return result[0]["profile_count"] if result else 0
    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = AuraConnection()

    query = """
    MATCH (p:Profile {email: $email})
    OPTIONAL MATCH (p)-[:HAS_ROLE]->(r:Role)
    RETURN
        p.id AS id,
        p.name AS name,
        p.email AS email,
        p.password_hash AS password_hash,
        p.auth_provider AS auth_provider,
        p.google_sub AS google_sub,
        r.role_id AS role_id,
        r.role_name AS role
    LIMIT 1
    """

    try:
        result = conn.execute_query(query, {
            "email": email.lower().strip()
        })

        if not result:
            return None

        return result[0]
    finally:
        conn.close()


def register_user_with_password(
    name: str,
    email: str,
    password: str,
    selected_role: str
):
    existing_user = get_user_by_email(email)

    if existing_user:
        return {
            "success": False,
            "message": "User already exists."
        }

    is_first_user = count_profiles() == 0

    final_role = "admin" if is_first_user else normalize_role(selected_role)
    final_role_id = get_role_id(final_role)

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)

    conn = AuraConnection()

    query = """
    MERGE (r:Role {role_id: $role_id})
    SET r.role_name = $role_name

    CREATE (p:Profile {
        id: $user_id,
        name: $name,
        email: $email,
        password_hash: $password_hash,
        auth_provider: "password",
        is_active: true,
        created_at: datetime(),
        updated_at: datetime()
    })

    MERGE (p)-[:HAS_ROLE]->(r)

    RETURN
        p.id AS id,
        p.name AS name,
        p.email AS email,
        r.role_id AS role_id,
        r.role_name AS role
    """

    try:
        result = conn.execute_write(query, {
            "user_id": user_id,
            "name": name.strip(),
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "role_id": final_role_id,
            "role_name": final_role
        })

        return {
            "success": True,
            "message": "User registered successfully.",
            "user": result[0]
        }
    finally:
        conn.close()


def login_user_with_password(email: str, password: str):
    user = get_user_by_email(email)

    if not user:
        return {
            "success": False,
            "message": "Invalid email or password."
        }

    password_hash = user.get("password_hash")

    if not password_hash:
        return {
            "success": False,
            "message": "This account uses Google login."
        }

    if not check_password_hash(password_hash, password):
        return {
            "success": False,
            "message": "Invalid email or password."
        }

    return {
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role_id": user["role_id"],
            "role": user["role"]
        }
    }


def login_or_register_google_user(
    name: str,
    email: str,
    google_sub: str,
    selected_role: Optional[str] = None
):
    existing_user = get_user_by_email(email)

    if existing_user:
        conn = AuraConnection()

        query = """
        MATCH (p:Profile {email: $email})
        SET
            p.google_sub = coalesce(p.google_sub, $google_sub),
            p.last_login_at = datetime(),
            p.updated_at = datetime()

        WITH p
        OPTIONAL MATCH (p)-[:HAS_ROLE]->(r:Role)

        RETURN
            p.id AS id,
            p.name AS name,
            p.email AS email,
            r.role_id AS role_id,
            r.role_name AS role
        LIMIT 1
        """

        try:
            result = conn.execute_write(query, {
                "email": email.lower().strip(),
                "google_sub": google_sub
            })

            return {
                "success": True,
                "message": "Google login successful.",
                "user": result[0]
            }
        finally:
            conn.close()

    is_first_user = count_profiles() == 0

    final_role = "admin" if is_first_user else normalize_role(selected_role)
    final_role_id = get_role_id(final_role)

    user_id = str(uuid.uuid4())

    conn = AuraConnection()

    query = """
    MERGE (r:Role {role_id: $role_id})
    SET r.role_name = $role_name

    CREATE (p:Profile {
        id: $user_id,
        name: $name,
        email: $email,
        password_hash: null,
        auth_provider: "google",
        google_sub: $google_sub,
        is_active: true,
        created_at: datetime(),
        updated_at: datetime(),
        last_login_at: datetime()
    })

    MERGE (p)-[:HAS_ROLE]->(r)

    RETURN
        p.id AS id,
        p.name AS name,
        p.email AS email,
        r.role_id AS role_id,
        r.role_name AS role
    """

    try:
        result = conn.execute_write(query, {
            "user_id": user_id,
            "name": name.strip(),
            "email": email.lower().strip(),
            "google_sub": google_sub,
            "role_id": final_role_id,
            "role_name": final_role
        })

        return {
            "success": True,
            "message": "Google user registered successfully.",
            "user": result[0]
        }
    finally:
        conn.close()