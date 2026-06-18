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
            candidate_tasks=classification.get("candidate_tasks"),
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
    """Detect domain and task. Resume context is provided by clarification_router.

    NEW QUERY: classify normally.
    INTENT CLARIFICATION: classify the merged query (router-built), pinning the
        final domain to the authorized session domain; _apply_classification
        decides whether another clarification is still required.
    PARAMETER CLARIFICATION: restore task/domain from state with confidence 1.0;
        no classification (the task does not change).
    """
    if state.get("clarification_failed"):
        return state

    stage = state.get("clarification_stage")

    if stage == STAGE_PARAMETER:
        original = state.get("original_query") or state["user_query"]
        classification = {
            "domain": state.get("domain") or "logistics",
            "task": state.get("task") or "order_lookup",
            "confidence": 1.0,
            "source": "parameter_resume",
        }
        logger.info(
            "Intent parameter resume: domain=%s task=%s",
            classification["domain"],
            classification["task"],
        )
        return _apply_classification({**state, "user_query": original}, classification)

    if stage == STAGE_INTENT:
        domain_hint = state.get("domain") or state.get("coarse_domain")
        classification = classify_domain_task(
            state["user_query"],
            entities=state.get("entities") or {},
            domain_hint=domain_hint if domain_hint else None,
        )
        # Coarse RBAC was skipped this turn; pin the domain to the authorized one
        # so an intent answer can never silently cross into another domain.
        if state.get("domain"):
            classification["domain"] = state["domain"]
        logger.info(
            "Intent clarification reclassified: task=%s domain=%s confidence=%s",
            classification.get("task"),
            classification.get("domain"),
            classification.get("confidence"),
        )
        return _apply_classification(state, classification)

    coarse = state.get("coarse_domain")
    classification = classify_domain_task(
        state["user_query"],
        entities=state.get("entities") or {},
        domain_hint=coarse if coarse else None,
    )
    return _apply_classification(state, classification)
