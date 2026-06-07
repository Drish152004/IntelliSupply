"""Role-based access control service."""

from __future__ import annotations

import logging

from orchestrator.rbac.exceptions import (
    UnauthorizedTaskError,
    UnknownRoleError,
    UnknownTaskError,
)
from orchestrator.rbac.permissions import ALL_TASKS, ROLE_PERMISSIONS
from orchestrator.rbac.role_mapper import map_to_orchestrator_role

logger = logging.getLogger(__name__)


class RBACService:
    """Validates whether a role may execute a classified task."""

    def validate_role(self, role: str) -> str:
        """Normalize and validate that the role exists."""
        return map_to_orchestrator_role(role)

    def validate_task(self, task: str) -> str:
        """Normalize and validate that the task exists."""
        normalized = task.strip().lower()
        if normalized not in ALL_TASKS:
            raise UnknownTaskError(f"Unknown task: {task}")
        return normalized

    def is_allowed(self, role: str, task: str) -> bool:
        """Return True when the role may execute the task."""
        normalized_role = self.validate_role(role)
        normalized_task = self.validate_task(task)
        allowed_tasks = ROLE_PERMISSIONS[normalized_role]
        return normalized_task in allowed_tasks

    def check_access(self, role: str, task: str) -> bool:
        """
        Validate role and task, then return allow/deny.

        Raises UnknownRoleError or UnknownTaskError for invalid inputs.
        Returns True when access is granted, False when denied.
        """
        normalized_role = self.validate_role(role)
        normalized_task = self.validate_task(task)
        allowed = normalized_task in ROLE_PERMISSIONS[normalized_role]

        if allowed:
            logger.info(
                "RBAC ALLOW\nrole=%s\ntask=%s",
                normalized_role,
                normalized_task,
            )
        else:
            logger.info(
                "RBAC DENY\nrole=%s\ntask=%s",
                normalized_role,
                normalized_task,
            )

        return allowed

    def require_access(self, role: str, task: str) -> None:
        """Raise UnauthorizedTaskError when access is denied."""
        if not self.check_access(role, task):
            normalized_role = self.validate_role(role)
            normalized_task = self.validate_task(task)
            raise UnauthorizedTaskError(
                f"Role {normalized_role} is not allowed to execute {normalized_task}"
            )

    def denial_reason(self, role: str, task: str) -> str:
        """Build a user-facing denial reason string."""
        normalized_role = self.validate_role(role)
        normalized_task = self.validate_task(task)
        return (
            f"Role {normalized_role} is not allowed to execute {normalized_task}"
        )
