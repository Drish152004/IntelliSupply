"""
RBAC enforcement node for the orchestration graph.

Runs after intent classification and before agent routing.
"""

from __future__ import annotations

import json
import logging

from orchestrator.rbac.exceptions import (
    UnknownIdentityError,
    UnknownRoleError,
    UnknownTaskError,
)
from orchestrator.rbac.role_mapper import IDENTITY_REQUIRED_MESSAGE
from orchestrator.rbac.rbac_service import RBACService
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_rbac_service = RBACService()


def enforce_rbac(state: AgentState) -> AgentState:
    """Check whether the current user's role may execute the detected task."""
    role = state.get("user_role")
    task = state.get("task", "")

    if not task:
        logger.debug("RBAC skipped: no task classified yet")
        return {**state, "access_denied": False}

    if not role:
        return _deny(state, "", task, IDENTITY_REQUIRED_MESSAGE)

    try:
        allowed = _rbac_service.check_access(role, task)
    except UnknownIdentityError as exc:
        logger.warning("RBAC identity error: %s", exc)
        return _deny(state, role or "", task, str(exc))
    except UnknownRoleError as exc:
        logger.warning("RBAC configuration error: %s", exc)
        return _deny(state, role, task, str(exc))
    except UnknownTaskError as exc:
        logger.warning("RBAC configuration error: %s", exc)
        return _deny(state, role, task, str(exc))

    if allowed:
        return {**state, "access_denied": False}

    reason = _rbac_service.denial_reason(role, task)
    return _deny(state, role, task, reason)


def _deny(state: AgentState, role: str, task: str, reason: str) -> AgentState:
    return {
        **state,
        "access_denied": True,
        "agent_response": json.dumps(
            {"status": "denied", "reason": reason},
            indent=2,
        ),
    }
