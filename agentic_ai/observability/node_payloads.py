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

    if node_name == "entity_resolution":
        entities = state.get("entities") or {}
        return {
            "task": state.get("task", ""),
            "domain": state.get("domain", ""),
            "entities": entities,
        }

    if node_name == "parameter_preparation":
        return {
            "task": state.get("task", ""),
            "domain": state.get("domain", ""),
            "entities": state.get("entities") or {},
        }

    if node_name == "rag_executor":
        return {
            "query": state.get("user_query", ""),
            "task": state.get("task", ""),
            "domain": state.get("domain", ""),
            "function_name": state.get("function_name"),
            "payload": state.get("payload") or {},
        }

    if node_name == "response_formatter":
        return {
            "task": state.get("task", ""),
            "execution_status": state.get("execution_status"),
            "clarification_needed": state.get("clarification_needed", False),
            "authorization_denied": state.get("authorization_denied", False),
            "access_denied": state.get("access_denied", False),
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

    if node_name == "entity_resolution":
        from orchestrator.entity_resolution_node import get_entity_resolution_records

        before_entities = before.get("entities") or {}
        after_entities = after.get("entities") or {}
        resolutions = get_entity_resolution_records()
        if not resolutions:
            resolutions = _entity_resolution_diff(before_entities, after_entities)
        return {
            "entities_before": before_entities,
            "entities_after": after_entities,
            "resolutions": resolutions,
        }

    if node_name == "parameter_preparation":
        return {
            "complete": not after.get("missing_required_parameters", False),
            "missing_fields": after.get("missing_fields") or [],
            "clarification_needed": after.get("clarification_needed", False),
            "function_name": after.get("function_name"),
            "payload": after.get("payload") or {},
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

    return {"node": node_name}


def _entity_resolution_diff(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[dict[str, Any]]:
    """Summarize per-key entity resolution outcomes for NODE_OUTPUT."""
    keys = sorted(set(before) | set(after))
    resolutions: list[dict[str, Any]] = []
    for key in keys:
        old_val = before.get(key)
        new_val = after.get(key)
        if old_val is None or not str(old_val).strip():
            continue
        before_text = str(old_val).strip()
        after_text = str(new_val).strip() if new_val is not None else None
        if before_text == after_text:
            status = "unchanged"
        elif after_text:
            status = "success"
        else:
            status = "failure"
        resolutions.append(
            {
                "entity_key": key,
                "before": before_text,
                "after": after_text,
                "status": status,
            }
        )
    return resolutions


def _response_status(state: AgentState) -> str:
    if state.get("clarification_failed"):
        return "clarification_failed"
    if state.get("authorization_denied"):
        return "authorization_denied"
    if state.get("access_denied"):
        return "access_denied"
    if state.get("clarification_needed"):
        return "clarification_required"
    if state.get("execution_status") == "error":
        return "error"
    return "success"
