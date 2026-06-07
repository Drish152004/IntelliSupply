"""Shared role definitions aligned with Supabase public.roles."""

from __future__ import annotations

from typing import Optional

ROLE_MAP = {
    "admin": 1,
    "courier": 2,
    "logistics_manager": 3,
    "inventory_manager": 4,
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
    return ROLE_MAP[normalize_role(role_name)]
