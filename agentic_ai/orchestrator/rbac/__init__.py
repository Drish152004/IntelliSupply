"""Role-based access control for orchestration."""

from orchestrator.rbac.courier_identity import (
    COURIER_IDENTITY_NOT_BOUND,
    resolve_courier_identity,
)
from orchestrator.rbac.exceptions import (
    UnknownIdentityError,
    UnknownRoleError,
)
from orchestrator.rbac.role_mapper import (
    AUTH_TO_ORCHESTRATOR,
    IDENTITY_REQUIRED_MESSAGE,
    map_to_orchestrator_role,
)
from orchestrator.rbac.session_context import (
    build_session_for_response,
    merge_logistics_session,
    restore_user_role,
)

__all__ = [
    "AUTH_TO_ORCHESTRATOR",
    "COURIER_IDENTITY_NOT_BOUND",
    "IDENTITY_REQUIRED_MESSAGE",
    "UnknownIdentityError",
    "UnknownRoleError",
    "build_session_for_response",
    "map_to_orchestrator_role",
    "merge_logistics_session",
    "resolve_courier_identity",
    "restore_user_role",
]
