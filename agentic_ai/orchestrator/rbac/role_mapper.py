"""Map auth-layer role names to orchestrator RBAC roles."""

from __future__ import annotations

from orchestrator.rbac.exceptions import UnknownIdentityError, UnknownRoleError
from orchestrator.task_registry import VALID_ROLES

AUTH_TO_ORCHESTRATOR: dict[str, str] = {
    "admin": "ADMIN",
    "logistics_manager": "LOGISTICS",
    "inventory_manager": "INVENTORY",
    "courier": "COURIER",
}

IDENTITY_REQUIRED_MESSAGE = "User identity not provided"


def map_to_orchestrator_role(role: str | None) -> str:
    """
    Normalize an auth or orchestrator role string to a valid orchestrator role.

    Raises UnknownIdentityError when role is missing/blank.
    Raises UnknownRoleError when the role is not recognized.
    """
    if role is None or not str(role).strip():
        raise UnknownIdentityError(IDENTITY_REQUIRED_MESSAGE)

    stripped = str(role).strip()
    upper = stripped.upper()
    if upper in VALID_ROLES:
        return upper

    mapped = AUTH_TO_ORCHESTRATOR.get(stripped.lower())
    if mapped:
        return mapped

    raise UnknownRoleError(f"Unknown role: {role}")
