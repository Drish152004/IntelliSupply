"""Parameter resolution: entity extraction and ENTITY clarification only."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationType
from context.entity_extractor import EntityExtractor
from context.query_completeness_checker import QueryCompletenessChecker
from orchestrator.resource_rbac import apply_self_scoped_entities, detect_self_scoped_task
from orchestrator.task_registry import VALID_DOMAINS
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def resolve_parameters(state: AgentState) -> AgentState:
    """
    Extract entities and request ENTITY HITL when logistics tasks lack identifiers.

    Authorization runs in the separate authorize_request node.
    """
    task = state.get("task", "")
    domain = state.get("domain", "")
    user_query = state["user_query"]
    user_role = state.get("user_role")

    updated: AgentState = {
        **state,
        "clarification_needed": False,
        "clarification_type": None,
        "clarification_question": None,
        "missing_fields": [],
    }

    if domain not in VALID_DOMAINS or domain == "inventory" or task == "inventory_nlsql":
        return updated

    entities = state.get("entities") or EntityExtractor.extract(user_query)
    entities = apply_self_scoped_entities(
        entities=entities,
        user_query=user_query,
        user_role=user_role,
        session=state.get("logistics_session"),
    )

    suggested = detect_self_scoped_task(user_query)
    if suggested and user_role == "COURIER" and entities.get("self_scoped") == "true":
        task = suggested
        domain = "logistics"
        updated["task"] = task
        updated["domain"] = domain

    updated["entities"] = entities

    if task == "city_lookup":
        return updated

    result = QueryCompletenessChecker.check(task, entities)

    if result.complete:
        return updated

    agent_response = json.dumps(
        {
            "status": "awaiting_input",
            "clarification_type": ClarificationType.ENTITY.value,
            "question": result.question,
            "missing_entities": result.missing_entities,
        },
        indent=2,
    )
    session_patch = _session_for_hitl({**updated, "task": task, "domain": domain})
    return {
        **updated,
        "task": task,
        "domain": domain,
        "clarification_needed": True,
        "clarification_type": ClarificationType.ENTITY.value,
        "clarification_question": result.question,
        "missing_fields": result.missing_entities or [],
        "agent_response": agent_response,
        "logistics_session": session_patch,
    }


def _session_for_hitl(state: AgentState) -> dict:
    base = dict(state.get("logistics_session") or state.get("inventory_session") or {})
    base["collecting"] = True
    base["task"] = state.get("task", "")
    base["domain"] = state.get("domain", "")
    if state.get("user_role"):
        base["user_role"] = state["user_role"]
    return base
