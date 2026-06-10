import logging

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.aura_profiles import sync_profile_to_aura
from rag.supabase import supabase_auth

logger = logging.getLogger(__name__)


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
    try:
        sync_profile_to_aura(
            profile_id=user["id"],
            name=user["name"],
            email=user["email"],
            role_id=user["role_id"],
            role_name=user["role"],
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
            )
        except Exception as exc:
            logger.warning("Aura sync failed on login: %s", exc)

    return result


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
