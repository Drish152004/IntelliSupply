"""RBAC-specific exceptions."""


class UnknownIdentityError(ValueError):
    """Raised when user identity or role is missing."""


class UnknownRoleError(ValueError):
    """Raised when a role is not recognized."""

