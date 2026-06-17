"""Direct RAG execution: inventory NL-SQL or Aura GraphDB logistics retrieval."""

from __future__ import annotations

import json
import logging

from context.query_completeness_checker import QueryCompletenessChecker
from integrations.aura_bridge import query_logistics
from integrations.sql_bridge import ask_inventory_sql
from orchestrator.state import AgentState
from orchestrator.task_registry import VALID_DOMAINS

logger = logging.getLogger(__name__)


def _blocked_missing_parameters(state: AgentState) -> AgentState | None:
    """Return a terminal state when required entities are missing."""
    if state.get("missing_required_parameters") or state.get("clarification_needed"):
        return {
            **state,
            "execution_status": "blocked",
            "execution_error": "missing_required_parameters",
            "agent_response": json.dumps(
                {
                    "status": "blocked",
                    "error_code": "MISSING_REQUIRED_PARAMETERS",
                    "missing_fields": state.get("missing_fields") or [],
                },
                indent=2,
            ),
        }

    domain = state.get("domain", "")
    task = state.get("task", "")
    if domain not in VALID_DOMAINS or domain == "inventory" or task in {
        "inventory_nlsql",
        "city_lookup",
    }:
        return None

    entities = state.get("entities") or {}
    completeness = QueryCompletenessChecker.check(task, entities)
    if completeness.complete:
        return None

    return {
        **state,
        "missing_required_parameters": True,
        "clarification_needed": True,
        "missing_fields": completeness.missing_entities or [],
        "execution_status": "blocked",
        "execution_error": "missing_required_parameters",
        "agent_response": json.dumps(
            {
                "status": "blocked",
                "error_code": "MISSING_REQUIRED_PARAMETERS",
                "missing_fields": completeness.missing_entities or [],
            },
            indent=2,
        ),
    }


def execute_rag(state: AgentState) -> AgentState:
    """Run the appropriate RAG backend based on domain."""
    blocked = _blocked_missing_parameters(state)
    if blocked is not None:
        return blocked

    domain = state.get("domain", "")
    task = state.get("task", "")
    query = state["user_query"]
    entities = state.get("entities") or {}
    trace_id = state.get("trace_id")

    routing_metadata = {
        "domain": domain,
        "task": task,
        "confidence": state.get("confidence"),
        "classification_source": state.get("classification_source"),
    }

    try:
        if domain == "inventory" or task == "inventory_nlsql":
            result = ask_inventory_sql(
                query,
                entities=entities,
                routing_metadata=routing_metadata,
                trace_id=trace_id,
            )
            status = "complete" if not result.get("error") else "error"
            agent_response = json.dumps(
                {
                    "status": status,
                    "domain": "inventory",
                    "task": task or "inventory_nlsql",
                    "answer": result.get("answer"),
                    "result": result,
                },
                indent=2,
                default=str,
            )
            return {
                **state,
                "execution_status": status,
                "execution_error": result.get("error"),
                "agent_response": agent_response,
            }

        result = query_logistics(
            user_query=query,
            task=task,
            entities=entities,
            prefetched_order_route=state.get("prefetched_order_route"),
            trace_id=trace_id,
        )
        status = "complete" if result.get("success") else "error"
        agent_response = json.dumps(
            {
                "status": status,
                "domain": "logistics",
                "task": task,
                "answer": result.get("answer"),
                "result": result,
            },
            indent=2,
            default=str,
        )
        return {
            **state,
            "execution_status": status,
            "execution_error": result.get("error"),
            "agent_response": agent_response,
        }

    except Exception as exc:
        logger.exception("RAG execution failed")
        return {
            **state,
            "execution_status": "error",
            "execution_error": str(exc),
            "agent_response": json.dumps(
                {"status": "error", "message": str(exc), "stage": "rag_execution"},
                indent=2,
            ),
        }
