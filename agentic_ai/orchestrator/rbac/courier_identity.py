"""Courier identity binding for orchestrator sessions."""

from __future__ import annotations

from typing import Any

from orchestrator.rbac.exceptions import UnknownIdentityError
from orchestrator.rbac.role_mapper import map_to_orchestrator_role

COURIER_IDENTITY_NOT_BOUND = "Courier identity not bound"


def resolve_courier_identity(authenticated_user: dict[str, Any] | None) -> dict[str, Any]:
    """
    Resolve authenticated user into orchestrator identity and session bindings.

    Returns:
        {
            "user_role": "<ADMIN|LOGISTICS|INVENTORY|COURIER>",
            "logistics_session": {"courier_id": "..."}  # when courier_id present
        }
    """
    if not authenticated_user:
        raise UnknownIdentityError("User identity not provided")

    user_role = map_to_orchestrator_role(authenticated_user.get("role"))

    logistics_session: dict[str, Any] = {}
    courier_id = authenticated_user.get("courier_id")
    if courier_id is not None and str(courier_id).strip():
        logistics_session["courier_id"] = str(courier_id).strip()

    logistics_session["user_role"] = user_role

    return {
        "user_role": user_role,
        "logistics_session": logistics_session,
    }
