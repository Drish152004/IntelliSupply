"""Post-intent authorization: task permissions and resource ownership."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationType
from orchestrator.resource_rbac import (
    AUTHZ_ALLOW,
    AUTHZ_DEFER,
    authorize_task_and_resources,
)
from orchestrator.state import AgentState
from orchestrator.task_registry import DYNAMIC_GRAPH_QUERY

logger = logging.getLogger(__name__)


def authorize_request(state: AgentState) -> AgentState:
    """Apply task-level and resource-level authorization after entity extraction.

    Outcomes:
      ALLOW -> clear denial flags and continue (unchanged behavior).
      DENY  -> mark authorization_denied + denial response (unchanged behavior).
      DEFER -> ownership not yet evaluable (scope missing); mark
               authorization_deferred WITHOUT denying, and fall through to
               parameter_preparation so it can collect the missing scope via
               HITL. The graph routes anything not authorization_denied to
               parameter_preparation, so execution is still only reached on a
               later ALLOW pass.
    """
    if state.get("missing_required_parameters") or state.get("clarification_needed"):
        return state

    status, reason, entities, prefetched_order_route = authorize_task_and_resources(state)

    updated: AgentState = {
        **state,
        "entities": entities,
        "authorization_denied": False,
        "access_denied": False,
        "authorization_status": status,
        "authorization_deferred": False,
        "authorization_scope": None,
    }
    if prefetched_order_route is not None:
        updated["prefetched_order_route"] = prefetched_order_route

    if status == AUTHZ_ALLOW:
        # Hand a concrete scope to dynamic execution: couriers are confined to
        # their own data; ADMIN/LOGISTICS are unscoped (None).
        if state.get("user_role") == "COURIER" and state.get("task") == DYNAMIC_GRAPH_QUERY:
            bound = (str(state.get("bound_courier_id") or "")).strip() or None
            updated["authorization_scope"] = {"courier_id": bound} if bound else None
        return updated

    if status == AUTHZ_DEFER:
        logger.info(
            "Authorization deferred: %s task=%s role=%s",
            reason,
            state.get("task"),
            state.get("user_role"),
        )
        updated["authorization_deferred"] = True
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
