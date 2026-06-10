"""Sync Supabase profile records into Neo4j Aura Profile nodes."""
from __future__ import annotations
from aura_graphdb.aura_connection import AuraConnection

def sync_profile_to_aura(
    *,
    profile_id: str,
    name: str,
    email: str,
    role_id: int,
    role_name: str,
    auth_provider: str = "password",
) -> dict:
    """Create or update a Profile node and its Role relationship in Aura."""
    conn = AuraConnection()

    query = """
    MERGE (r:Role {role_id: toInteger($role_id)})
    ON CREATE SET
        r.created_at = datetime()
    SET
        r.role_name = $role_name,
        r.updated_at = datetime()

    MERGE (p:Profile {id: $profile_id})
    ON CREATE SET
        p.created_at = datetime()
    SET
        p.name = $name,
        p.email = toLower(trim($email)),
        p.auth_provider = $auth_provider,
        p.source = "supabase",
        p.is_active = true,
        p.updated_at = datetime()

    MERGE (p)-[:HAS_ROLE]->(r)

    RETURN
        p.id AS id,
        p.name AS name,
        p.email AS email,
        r.role_id AS role_id,
        r.role_name AS role_name
    """

    try:
        result = conn.execute_write(
            query,
            {
                "profile_id": str(profile_id),
                "name": name.strip(),
                "email": email.lower().strip(),
                "role_id": int(role_id),
                "role_name": role_name,
                "auth_provider": auth_provider,
            },
        )

        if not result:
            raise RuntimeError("Aura profile sync returned no rows.")

        return result[0]

    finally:
        conn.close()


def sync_all_profiles_from_supabase() -> int:
    """Load every Supabase profile into Aura."""
    from rag.supabase.supabase_auth import list_profiles_with_roles

    profiles = list_profiles_with_roles()

    for profile in profiles:
        sync_profile_to_aura(
            profile_id=profile["id"],
            name=profile["name"],
            email=profile["email"],
            role_id=profile["role_id"],
            role_name=profile["role"],
        )

    return len(profiles)