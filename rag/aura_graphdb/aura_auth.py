import logging
import uuid
from typing import Optional

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.aura_profiles import sync_profile_to_aura
from aura_graphdb import supabase_auth

logger = logging.getLogger(__name__)

from aura_graphdb.aura_roles import ALLOWED_ROLES, ROLE_MAP, get_role_id, normalize_role


def count_profiles() -> int:
    return supabase_auth.count_profiles()


def get_user_by_email(email: str):
    return supabase_auth.get_user_by_email(email)


def get_user_by_id(user_id: str):
    return supabase_auth.get_user_by_id(user_id)


def update_user_profile(user_id: str, *, name: str | None = None):
    updated = supabase_auth.update_user_profile(user_id, name=name)
    if not updated:
        return None
    try:
        sync_profile_to_aura(
            profile_id=updated["id"],
            name=updated["name"],
            email=updated["email"],
            role_id=updated["role_id"],
            role_name=updated["role"],
            password_hash=updated.get("password_hash"),
        )
    except Exception as exc:
        logger.warning("Aura sync failed after profile update: %s", exc)
    return updated


def register_user_with_password(
    name: str,
    email: str,
    password: str,
    selected_role: str,
):
    supabase_result = supabase_auth.register_user_in_supabase(
        name=name,
        email=email,
        password=password,
        selected_role=selected_role,
    )

    if not supabase_result["success"]:
        return supabase_result

    user = supabase_result["user"]
    stored = supabase_auth.get_user_by_email(user["email"])
    try:
        sync_profile_to_aura(
            profile_id=user["id"],
            name=user["name"],
            email=user["email"],
            role_id=user["role_id"],
            role_name=user["role"],
            password_hash=stored.get("password_hash") if stored else None,
        )
    except Exception as exc:
        logger.warning("Aura sync failed: %s", exc)

    return supabase_result


def login_user_with_password(email: str, password: str):
    result = supabase_auth.login_user_with_password(email=email, password=password)
    if not result["success"]:
        return result

    user = result["user"]
    stored = supabase_auth.get_user_by_email(user["email"])
    if stored:
        try:
            sync_profile_to_aura(
                profile_id=stored["id"],
                name=stored["name"],
                email=stored["email"],
                role_id=stored["role_id"],
                role_name=stored["role"],
                password_hash=stored.get("password_hash"),
            )
        except Exception as exc:
            logger.warning("Aura sync failed on login: %s", exc)

    return result


def login_or_register_google_user(
    name: str,
    email: str,
    google_sub: str,
    selected_role: Optional[str] = None,
):
    """Google OAuth still stores profiles directly in Aura (no Supabase auth.users integration yet)."""
    existing_user = _get_aura_profile_by_email(email)

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
            result = conn.execute_write(
                query,
                {
                    "email": email.lower().strip(),
                    "google_sub": google_sub,
                },
            )

            return {
                "success": True,
                "message": "Google login successful.",
                "user": result[0],
            }
        finally:
            conn.close()

    is_first_user = _count_aura_profiles() == 0 and count_profiles() == 0

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
        result = conn.execute_write(
            query,
            {
                "user_id": user_id,
                "name": name.strip(),
                "email": email.lower().strip(),
                "google_sub": google_sub,
                "role_id": final_role_id,
                "role_name": final_role,
            },
        )

        return {
            "success": True,
            "message": "Google user registered successfully.",
            "user": result[0],
        }
    finally:
        conn.close()


def list_all_users(limit: int = 100):
    """Return Supabase profiles plus Aura courier accounts."""
    profiles = supabase_auth.list_all_users(limit=limit)
    conn = AuraConnection()

    query = """
    MATCH (c:Courier)
    OPTIONAL MATCH (c)-[:HAS_ROLE]->(r:Role)
    RETURN
        c.courier_id AS id,
        c.name AS name,
        c.email AS email,
        coalesce(r.role_name, 'courier') AS role,
        'Courier' AS account_type,
        coalesce(c.is_active, true) AS is_active,
        c.created_at AS created_at
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    try:
        couriers = conn.execute_query(query, {"limit": int(limit)})
    finally:
        conn.close()

    combined = profiles + [
        {
            "id": row.get("id"),
            "name": row.get("name") or f"Courier {str(row.get('id') or '')[:8]}",
            "email": row.get("email") or "",
            "role": row.get("role"),
            "account_type": row.get("account_type"),
            "is_active": row.get("is_active", True),
        }
        for row in couriers
    ]
    return combined[:limit]


def _count_aura_profiles() -> int:
    conn = AuraConnection()
    query = "MATCH (p:Profile) RETURN count(p) AS profile_count"
    try:
        result = conn.execute_query(query)
        return result[0]["profile_count"] if result else 0
    finally:
        conn.close()


def _get_aura_profile_by_email(email: str):
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
        result = conn.execute_query(query, {"email": email.lower().strip()})
        return result[0] if result else None
    finally:
        conn.close()
