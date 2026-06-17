"""Parameter validation: completeness checks and ENTITY clarification only."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationType
from context.query_completeness_checker import QueryCompletenessChecker
from orchestrator.hitl_session import (
    MAX_HITL_ATTEMPTS,
    STAGE_PARAMETER,
    attach_clarification_session,
    attempts_exceeded,
    build_clarification_session,
    clarification_type_for_stage,
    get_active_hitl_session,
)
from orchestrator.task_registry import VALID_DOMAINS
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _clarification_failed_state(state: AgentState) -> AgentState:
    return {
        **state,
        "clarification_needed": False,
        "clarification_failed": True,
        "agent_response": json.dumps(
            {
                "status": "clarification_failed",
                "message": (
                    f"Unable to collect required information after "
                    f"{MAX_HITL_ATTEMPTS} attempts."
                ),
            },
            indent=2,
        ),
    }


def validate_parameters(state: AgentState) -> AgentState:
    """
    Verify required entities exist for the resolved task.

    Uses state["entities"] from entity_extraction; does not extract or authorize.
    When parameters are missing, sets missing_required_parameters and clarification_needed.
    """
    if state.get("clarification_failed"):
        return state

    task = state.get("task", "")
    domain = state.get("domain", "")
    entities = dict(state.get("entities") or {})

    updated: AgentState = {
        **state,
        "entities": entities,
        "clarification_needed": False,
        "missing_required_parameters": False,
        "clarification_type": None,
        "clarification_question": None,
        "missing_fields": [],
    }

    if domain not in VALID_DOMAINS or domain == "inventory" or task == "inventory_nlsql":
        return updated

    if task == "city_lookup":
        return updated

    result = QueryCompletenessChecker.check(task, entities)

    if result.complete:
        return updated

    active_session = get_active_hitl_session(state)
    if attempts_exceeded(active_session):
        logger.info("Parameter clarification attempt limit reached for task=%s", task)
        return {
            **_clarification_failed_state(updated),
            "missing_required_parameters": True,
        }

    agent_response = json.dumps(
        {
            "status": "awaiting_input",
            "clarification_type": ClarificationType.ENTITY.value,
            "question": result.question,
            "missing_entities": result.missing_entities,
        },
        indent=2,
    )
    session = build_clarification_session(
        updated,
        stage=STAGE_PARAMETER,
        clarification_type=clarification_type_for_stage(STAGE_PARAMETER),
        base_session=active_session,
    )
    patched = attach_clarification_session(updated, session, stage=STAGE_PARAMETER)
    return {
        **patched,
        "missing_required_parameters": True,
        "clarification_needed": True,
        "clarification_stage": STAGE_PARAMETER,
        "clarification_type": ClarificationType.ENTITY.value,
        "clarification_question": result.question,
        "missing_fields": result.missing_entities or [],
        "agent_response": agent_response,
    }
