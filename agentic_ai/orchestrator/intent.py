"""Domain and task detection for orchestration routing."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationType
from orchestrator.intent_task_classifier import (
    build_clarification_question,
    classify_domain_task,
    needs_intent_clarification,
)
from orchestrator.resource_rbac import detect_self_scoped_task
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _session_collecting(session: dict | None) -> bool:
    return bool(session and session.get("collecting"))


def _apply_classification(state: AgentState, classification: dict) -> AgentState:
    domain = classification["domain"]
    task = classification["task"]
    confidence = classification["confidence"]

    updated: AgentState = {
        **state,
        "domain": domain,
        "task": task,
        "confidence": confidence,
        "clarification_needed": False,
        "clarification_type": None,
        "clarification_question": None,
    }

    if needs_intent_clarification(task, confidence):
        question = build_clarification_question(state["user_query"], classification)
        updated["clarification_needed"] = True
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
    """Detect domain and task from the user query and update state."""
    inventory_session = state.get("inventory_session")
    if _session_collecting(inventory_session):
        classification = {
            "domain": "inventory",
            "task": (inventory_session or {}).get("task") or "inventory_nlsql",
            "confidence": 1.0,
        }
        return _apply_classification(state, classification)

    logistics_session = state.get("logistics_session")
    if _session_collecting(logistics_session):
        classification = {
            "domain": "logistics",
            "task": (logistics_session or {}).get("task") or state.get("task") or "shipment_lookup",
            "confidence": 1.0,
        }
        return _apply_classification(state, classification)

    coarse = state.get("coarse_domain")
    classification = classify_domain_task(
        state["user_query"],
        domain_hint=coarse if coarse else None,
    )

    if state.get("user_role") == "COURIER":
        self_task = detect_self_scoped_task(state["user_query"])
        if self_task:
            classification = {
                "domain": "logistics",
                "task": self_task,
                "confidence": 0.95,
            }

    return _apply_classification(state, classification)
