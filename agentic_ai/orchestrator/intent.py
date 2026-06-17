"""Domain and task detection for orchestration routing."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationType
from orchestrator.hitl_session import (
    STAGE_INTENT,
    STAGE_PARAMETER,
    attach_clarification_session,
    build_clarification_session,
    clarification_type_for_stage,
    get_active_hitl_session,
    is_intent_resume,
    is_parameter_resume,
    merge_intent_query,
)
from orchestrator.intent_task_classifier import (
    build_clarification_question,
    classify_domain_task,
    needs_intent_clarification,
)
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _apply_classification(state: AgentState, classification: dict) -> AgentState:
    domain = classification["domain"]
    task = classification["task"]
    confidence = classification["confidence"]
    source = classification.get("source", "intent_classifier")

    updated: AgentState = {
        **state,
        "domain": domain,
        "task": task,
        "confidence": confidence,
        "classification_source": source,
        "clarification_needed": False,
        "clarification_stage": None,
        "clarification_type": None,
        "clarification_question": None,
    }

    if needs_intent_clarification(task, confidence):
        question = build_clarification_question(state["user_query"], classification)
        session = build_clarification_session(
            updated,
            stage=STAGE_INTENT,
            clarification_type=clarification_type_for_stage(STAGE_INTENT),
            base_session=get_active_hitl_session(state),
        )
        updated = attach_clarification_session(updated, session, stage=STAGE_INTENT)
        updated["clarification_needed"] = True
        updated["clarification_stage"] = STAGE_INTENT
        updated["clarification_type"] = ClarificationType.INTENT.value
        updated["clarification_question"] = question
        updated["agent_response"] = json.dumps(
            {
                "status": "awaiting_input",
                "clarification_type": ClarificationType.INTENT.value,
                "question": question,
            },
            indent=2,
        )

    return updated


def detect_intent(state: AgentState) -> AgentState:
    """Detect domain and task from query, entities, and session context."""
    if state.get("clarification_failed"):
        return state

    if is_parameter_resume(state):
        session = get_active_hitl_session(state) or {}
        domain = session.get("domain") or state.get("domain", "logistics")
        classification = {
            "domain": domain,
            "task": session.get("task") or state.get("task") or "shipment_lookup",
            "confidence": 1.0,
            "source": "parameter_resume",
        }
        logger.info(
            "Intent parameter resume: domain=%s task=%s",
            classification["domain"],
            classification["task"],
        )
        return _apply_classification(state, classification)

    if is_intent_resume(state):
        session = get_active_hitl_session(state) or {}
        original = session.get("original_query") or state.get("original_query", "")
        merged_query = merge_intent_query(original, state["user_query"])
        logger.info("Intent resume merged query: %r", merged_query)
        coarse = state.get("coarse_domain") or session.get("domain")
        entities = state.get("entities") or {}
        classification = classify_domain_task(
            merged_query,
            entities=entities,
            domain_hint=coarse if coarse else None,
        )
        resumed_state: AgentState = {**state, "user_query": merged_query}
        return _apply_classification(resumed_state, classification)

    coarse = state.get("coarse_domain")
    entities = state.get("entities") or {}
    classification = classify_domain_task(
        state["user_query"],
        entities=entities,
        domain_hint=coarse if coarse else None,
    )

    return _apply_classification(state, classification)
