"""Post-intent authorization: task permissions and resource ownership."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationType
from orchestrator.resource_rbac import authorize_task_and_resources
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def authorize_request(state: AgentState) -> AgentState:
    """Apply task-level and resource-level authorization after entity extraction."""
    if state.get("missing_required_parameters") or state.get("clarification_needed"):
        return state

    allowed, reason, entities, prefetched_order_route = authorize_task_and_resources(state)

    updated: AgentState = {
        **state,
        "entities": entities,
        "authorization_denied": False,
        "access_denied": False,
    }
    if prefetched_order_route is not None:
        updated["prefetched_order_route"] = prefetched_order_route

    if allowed:
        return updated

    logger.info("Authorization denied: %s task=%s role=%s", reason, state.get("task"), state.get("user_role"))
    return {
        **updated,
        "authorization_denied": True,
        "access_denied": False,
        "clarification_type": ClarificationType.AUTHORIZATION.value,
        "agent_response": json.dumps(
            {
                "status": "authorization_denied",
                "clarification_type": ClarificationType.AUTHORIZATION.value,
                "reason": reason,
            },
            indent=2,
        ),
    }
