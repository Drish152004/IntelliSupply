"""Role-based access control for orchestration."""

from orchestrator.rbac.courier_identity import (
    COURIER_IDENTITY_NOT_BOUND,
    resolve_courier_identity,
)
from orchestrator.rbac.exceptions import (
    UnauthorizedTaskError,
    UnknownIdentityError,
    UnknownRoleError,
    UnknownTaskError,
)
from orchestrator.rbac.permissions import ALL_TASKS, ROLE_PERMISSIONS, VALID_ROLES
from orchestrator.rbac.rbac_service import RBACService
from orchestrator.rbac.role_mapper import (
    AUTH_TO_ORCHESTRATOR,
    IDENTITY_REQUIRED_MESSAGE,
    map_to_orchestrator_role,
)
from orchestrator.rbac.session_context import (
    build_session_for_response,
    merge_logistics_session,
    persist_rbac_context,
    restore_user_role,
)

__all__ = [
    "ALL_TASKS",
    "AUTH_TO_ORCHESTRATOR",
    "COURIER_IDENTITY_NOT_BOUND",
    "IDENTITY_REQUIRED_MESSAGE",
    "ROLE_PERMISSIONS",
    "RBACService",
    "UnauthorizedTaskError",
    "UnknownIdentityError",
    "UnknownRoleError",
    "UnknownTaskError",
    "VALID_ROLES",
    "build_session_for_response",
    "map_to_orchestrator_role",
    "merge_logistics_session",
    "persist_rbac_context",
    "resolve_courier_identity",
    "restore_user_role",
]
