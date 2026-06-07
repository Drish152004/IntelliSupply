"""Supabase-backed profile authentication (source of truth)."""

from __future__ import annotations

import uuid
from typing import Any

import bcrypt
from sqlalchemy import text

from aura_graphdb.aura_roles import get_role_id, normalize_role
from aura_graphdb.supabase_connection import get_supabase_engine


def _engine():
    return get_supabase_engine()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=6)).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def count_profiles() -> int:
    with _engine().connect() as conn:
        return int(conn.execute(text("SELECT count(*) FROM profiles")).scalar() or 0)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    query = text(
        """
        SELECT
            p.id::text AS id,
            p.name AS name,
            p.email AS email,
            p.password_hash AS password_hash,
            r.role_id AS role_id,
            r.role_name AS role
        FROM profiles p
        JOIN user_roles ur ON ur.user_id = p.id
        JOIN roles r ON r.role_id = ur.role_id
        WHERE lower(p.email) = lower(:email)
        LIMIT 1
        """
    )
    with _engine().connect() as conn:
        row = conn.execute(query, {"email": email.strip()}).mappings().first()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    query = text(
        """
        SELECT
            p.id::text AS id,
            p.name AS name,
            p.email AS email,
            p.password_hash AS password_hash,
            r.role_id AS role_id,
            r.role_name AS role
        FROM profiles p
        JOIN user_roles ur ON ur.user_id = p.id
        JOIN roles r ON r.role_id = ur.role_id
        WHERE p.id::text = :user_id
        LIMIT 1
        """
    )
    with _engine().connect() as conn:
        row = conn.execute(query, {"user_id": str(user_id)}).mappings().first()
        return dict(row) if row else None


def list_profiles_with_roles(limit: int = 500) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            p.id::text AS id,
            p.name AS name,
            p.email AS email,
            p.password_hash AS password_hash,
            r.role_id AS role_id,
            r.role_name AS role
        FROM profiles p
        JOIN user_roles ur ON ur.user_id = p.id
        JOIN roles r ON r.role_id = ur.role_id
        ORDER BY p.created_at DESC
        LIMIT :limit
        """
    )
    with _engine().connect() as conn:
        rows = conn.execute(query, {"limit": int(limit)}).mappings().all()
        return [dict(row) for row in rows]


def list_all_users(limit: int = 100) -> list[dict[str, Any]]:
    profiles = list_profiles_with_roles(limit=limit)
    return [
        {
            "id": profile["id"],
            "name": profile["name"],
            "email": profile["email"],
            "role": profile["role"],
            "account_type": "Profile",
            "is_active": True,
        }
        for profile in profiles
    ]


def update_user_profile(user_id: str, *, name: str | None = None) -> dict[str, Any] | None:
    if not name:
        return get_user_by_id(user_id)

    query = text(
        """
        UPDATE profiles
        SET name = :name
        WHERE id::text = :user_id
        RETURNING id::text AS id, name, email
        """
    )
    with _engine().begin() as conn:
        row = conn.execute(query, {"user_id": str(user_id), "name": name.strip()}).mappings().first()
        if not row:
            return None
        profile = get_user_by_id(user_id)
        return profile


def register_user_in_supabase(
    name: str,
    email: str,
    password: str,
    selected_role: str,
) -> dict[str, Any]:
    existing = get_user_by_email(email)
    if existing:
        return {"success": False, "message": "User already exists."}

    is_first_user = count_profiles() == 0
    final_role = "admin" if is_first_user else normalize_role(selected_role)
    if final_role not in ALLOWED_ROLES:
        final_role = "courier"
    final_role_id = get_role_id(final_role)

    profile_id = str(uuid.uuid4())
    password_hash = _hash_password(password)

    insert_profile = text(
        """
        INSERT INTO profiles (id, name, email, password_hash)
        VALUES (:id::uuid, :name, :email, :password_hash)
        """
    )
    insert_role = text(
        """
        INSERT INTO user_roles (user_id, role_id)
        VALUES (:user_id::uuid, :role_id)
        """
    )

    with _engine().begin() as conn:
        conn.execute(
            insert_profile,
            {
                "id": profile_id,
                "name": name.strip(),
                "email": email.lower().strip(),
                "password_hash": password_hash,
            },
        )
        conn.execute(
            insert_role,
            {
                "user_id": profile_id,
                "role_id": final_role_id,
            },
        )

    user = {
        "id": profile_id,
        "name": name.strip(),
        "email": email.lower().strip(),
        "role_id": final_role_id,
        "role": final_role,
    }
    return {
        "success": True,
        "message": "User registered successfully.",
        "user": user,
    }


def login_user_with_password(email: str, password: str) -> dict[str, Any]:
    user = get_user_by_email(email)
    if not user:
        return {"success": False, "message": "Invalid email or password."}

    password_hash = user.get("password_hash")
    if not password_hash or not _verify_password(password, password_hash):
        return {"success": False, "message": "Invalid email or password."}

    return {
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role_id": user["role_id"],
            "role": user["role"],
        },
    }
