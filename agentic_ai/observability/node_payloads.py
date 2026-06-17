"""Node boundary payload extractors for structured orchestration tracing."""

from __future__ import annotations

from typing import Any

from orchestrator.state import AgentState


def extract_node_input(node_name: str, state: AgentState) -> dict[str, Any]:
    """Build a concise NODE_INPUT payload for a graph node."""
    if node_name == "init_state":
        return {
            "query": state.get("user_query", ""),
            "role": state.get("user_role"),
            "language_hint": state.get("language_hint"),
        }

    if node_name == "coarse_authorization":
        return {
            "query": state.get("user_query", ""),
            "role": state.get("user_role"),
        }

    if node_name == "entity_extraction":
        return {
            "query": state.get("user_query", ""),
            "domain": state.get("coarse_domain") or state.get("domain"),
            "role": state.get("user_role"),
        }

    if node_name == "intent":
        return {
            "query": state.get("user_query", ""),
            "entities": state.get("entities") or {},
            "coarse_domain": state.get("coarse_domain"),
        }

    if node_name == "parameter_validation":
        return {
            "task": state.get("task", ""),
            "domain": state.get("domain", ""),
            "entities": state.get("entities") or {},
        }

    if node_name == "semantic_cache_lookup":
        return {
            "query": state.get("user_query", ""),
            "role": state.get("user_role"),
            "domain": state.get("domain"),
            "task": state.get("task", ""),
            "entities": state.get("entities") or {},
        }

    if node_name == "authorize":
        return {
            "task": state.get("task", ""),
            "domain": state.get("domain", ""),
            "role": state.get("user_role"),
            "entities": state.get("entities") or {},
        }

    if node_name == "rag_executor":
        return {
            "query": state.get("user_query", ""),
            "task": state.get("task", ""),
            "domain": state.get("domain", ""),
            "entities": state.get("entities") or {},
        }

    if node_name == "response_formatter":
        return {
            "task": state.get("task", ""),
            "cache_hit": state.get("cache_hit", False),
            "execution_status": state.get("execution_status"),
            "clarification_needed": state.get("clarification_needed", False),
            "authorization_denied": state.get("authorization_denied", False),
            "access_denied": state.get("access_denied", False),
        }

    if node_name == "semantic_cache_store":
        return {
            "query": state.get("user_query", ""),
            "task": state.get("task", ""),
            "domain": state.get("domain", ""),
            "cache_key": state.get("cache_key"),
            "execution_status": state.get("execution_status"),
        }

    return {"node": node_name}


def extract_node_output(node_name: str, before: AgentState, after: AgentState) -> dict[str, Any]:
    """Build a concise NODE_OUTPUT payload for a graph node."""
    if node_name == "init_state":
        return {
            "query": after.get("user_query", ""),
            "role": after.get("user_role"),
            "detected_language": after.get("detected_language"),
        }

    if node_name == "coarse_authorization":
        return {
            "authorized": after.get("authorized", False),
            "domain": after.get("coarse_domain") or after.get("authorized_domain"),
            "access_denied": after.get("access_denied", False),
            "clarification_needed": after.get("clarification_needed", False),
            "reason": after.get("classification_source", "keyword_match"),
        }

    if node_name == "entity_extraction":
        return {"entities": after.get("entities") or {}}

    if node_name == "intent":
        return {
            "domain": after.get("domain", ""),
            "task": after.get("task", ""),
            "confidence": after.get("confidence", 0.0),
            "clarification_needed": after.get("clarification_needed", False),
            "classification_source": after.get("classification_source"),
        }

    if node_name == "parameter_validation":
        return {
            "complete": not after.get("missing_required_parameters", False),
            "missing_fields": after.get("missing_fields") or [],
            "clarification_needed": after.get("clarification_needed", False),
        }

    if node_name == "semantic_cache_lookup":
        return {
            "hit": after.get("cache_hit", False),
            "cache_key": after.get("cache_key"),
        }

    if node_name == "authorize":
        return {
            "authorized": not after.get("authorization_denied", False),
            "authorization_denied": after.get("authorization_denied", False),
            "prefetched_order_route": bool(after.get("prefetched_order_route")),
        }

    if node_name == "rag_executor":
        return {
            "execution_status": after.get("execution_status"),
            "execution_error": after.get("execution_error"),
        }

    if node_name == "response_formatter":
        return {
            "status": _response_status(after),
            "final_response_chars": len(after.get("final_response") or ""),
        }

    if node_name == "semantic_cache_store":
        return {
            "cache_key": after.get("cache_key"),
            "stored": bool(after.get("cache_key")),
        }

    return {"node": node_name}


def _response_status(state: AgentState) -> str:
    if state.get("clarification_failed"):
        return "clarification_failed"
    if state.get("authorization_denied"):
        return "authorization_denied"
    if state.get("access_denied"):
        return "access_denied"
    if state.get("clarification_needed"):
        return "clarification_required"
    if state.get("cache_hit"):
        return "cache_hit"
    if state.get("execution_status") == "error":
        return "error"
    return "success"
