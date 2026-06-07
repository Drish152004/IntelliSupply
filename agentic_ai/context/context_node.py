"""Orchestrator nodes for query completeness and context resolution (Phase 5)."""

from __future__ import annotations

import json
import logging

from context.entity_extractor import EntityExtractor
from context.query_completeness_checker import QueryCompletenessChecker
from context.resolver import get_context_resolver
from context.task_requirements import is_ml_task
from graph_retrieval.graph_authorizer import GraphAuthorizer
from orchestrator.resource_rbac import authorize_courier_resource
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def check_query_completeness(state: AgentState) -> AgentState:
    """HITL #1: verify minimum query entities exist before graph search."""
    task = state.get("task", "")
    user_query = state["user_query"]
    session = state.get("logistics_session")

    updated: AgentState = {
        **state,
        "clarification_needed": False,
        "clarification_type": None,
        "clarification_question": None,
    }

    if not is_ml_task(task):
        return updated

    entities = state.get("entities") or EntityExtractor.extract(user_query)
    entities = GraphAuthorizer.resolve_courier_id(
        entities=entities,
        user_query=user_query,
        session=session,
    )
    updated["entities"] = entities

    logger.info("QUERY COMPLETENESS CHECK\ntask=%s\nentities=%s", task, entities)
    result = QueryCompletenessChecker.check(task, entities)

    if result.complete:
        return updated

    agent_response = json.dumps(
        {
            "status": "awaiting_input",
            "needs_clarification": True,
            "clarification_type": result.clarification_type.value if result.clarification_type else "ENTITY",
            "question": result.question,
            "missing_entities": result.missing_entities,
        },
        indent=2,
    )
    return {
        **updated,
        "clarification_needed": True,
        "clarification_type": result.clarification_type.value if result.clarification_type else "ENTITY",
        "clarification_question": result.question,
        "agent_response": agent_response,
    }


def resolve_context(state: AgentState) -> AgentState:
    """HITL #2: enrich from Aura, build payload, detect missing fields."""
    task = state.get("task", "")
    entities = state.get("entities") or {}
    user_fields = dict(state.get("ml_payload_partial") or {})

    updated: AgentState = {
        **state,
        "ready_for_ml": False,
        "payload": None,
        "resolved_context": None,
        "graph_enriched_fields": [],
        "user_supplied_fields": [],
        "missing_fields": [],
        "clarification_needed": False,
        "clarification_type": None,
        "clarification_question": None,
    }

    if not is_ml_task(task):
        return updated

    allowed, reason, resolved_entities = authorize_courier_resource(state)
    if not allowed:
        return {
            **updated,
            "entities": resolved_entities,
            "authorization_denied": True,
            "agent_response": json.dumps(
                {"status": "denied", "reason": reason},
                indent=2,
            ),
        }

    entities = resolved_entities or entities
    resolution = get_context_resolver().resolve(task, entities, user_fields)

    base_update: AgentState = {
        **updated,
        "resolved_context": resolution.resolved_context,
        "payload": resolution.payload,
        "graph_enriched_fields": resolution.graph_enriched_fields or [],
        "user_supplied_fields": resolution.user_supplied_fields or [],
        "missing_fields": resolution.missing_fields or [],
    }

    if resolution.ready_for_ml:
        agent_response = json.dumps(
            {
                "status": "ready_for_ml",
                "ready_for_ml": True,
                "task": task,
                "payload": resolution.payload,
                "graph_enriched_fields": resolution.graph_enriched_fields,
                "user_supplied_fields": resolution.user_supplied_fields,
                "missing_fields": [],
            },
            indent=2,
            default=str,
        )
        return {
            **base_update,
            "ready_for_ml": True,
            "agent_response": agent_response,
        }

    agent_response = json.dumps(
        {
            "status": "awaiting_input",
            "ready_for_ml": False,
            "needs_clarification": True,
            "clarification_type": (
                resolution.clarification_type.value if resolution.clarification_type else "PAYLOAD"
            ),
            "question": resolution.clarification_question,
            "missing_fields": resolution.missing_fields,
            "partial_payload": resolution.payload,
        },
        indent=2,
        default=str,
    )
    return {
        **base_update,
        "clarification_needed": True,
        "clarification_type": (
            resolution.clarification_type.value if resolution.clarification_type else "PAYLOAD"
        ),
        "clarification_question": resolution.clarification_question,
        "agent_response": agent_response,
    }
