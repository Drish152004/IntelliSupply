"""RBAC-specific exceptions."""


class UnknownIdentityError(ValueError):
    """Raised when user identity or role is missing."""


class UnknownRoleError(ValueError):
    """Raised when a role is not recognized."""


class UnknownTaskError(ValueError):
    """Raised when a task is not recognized."""


class UnauthorizedTaskError(PermissionError):
    """Raised when a role is not permitted to execute a task."""
