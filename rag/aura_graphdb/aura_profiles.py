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
    password_hash: str | None = None,
    auth_provider: str = "password",
) -> dict:
    """Create or update a Profile node and role relationship in Aura."""
    conn = AuraConnection()

    query = """
    MERGE (r:Role {role_id: toInteger($role_id)})
    SET r.role_name = $role_name

    MERGE (p:Profile {id: $profile_id})
    ON CREATE SET p.created_at = datetime()
    SET
        p.name = $name,
        p.email = toLower(trim($email)),
        p.auth_provider = $auth_provider,
        p.is_active = true,
        p.updated_at = datetime()

    FOREACH (_ IN CASE WHEN $password_hash IS NULL THEN [] ELSE [1] END |
        SET p.password_hash = $password_hash
    )

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
                "profile_id": str(profile_id),
                "name": name.strip(),
                "email": email.lower().strip(),
                "role_id": int(role_id),
                "role_name": role_name,
                "password_hash": password_hash,
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
    from aura_graphdb.supabase_auth import list_profiles_with_roles

    profiles = list_profiles_with_roles()
    for profile in profiles:
        sync_profile_to_aura(
            profile_id=profile["id"],
            name=profile["name"],
            email=profile["email"],
            role_id=profile["role_id"],
            role_name=profile["role"],
            password_hash=profile.get("password_hash"),
        )
    return len(profiles)
