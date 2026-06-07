"""
Domain and task detection for orchestration routing.

Uses intent_task_classifier for LLM-based classification with session-aware
short-circuits and low-confidence clarification handling.
"""

from __future__ import annotations

import json
import logging

from orchestrator.intent_task_classifier import (
    build_clarification_question,
    classify_domain_task,
    needs_intent_clarification,
)
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _session_collecting(session: dict | None) -> bool:
    return bool(session and session.get("collecting"))


def _apply_classification(state: AgentState, classification: dict) -> AgentState:
    domain = classification["domain"]
    task = classification["task"]
    confidence = classification["confidence"]

    logger.debug("Detected Domain: %s", domain)
    logger.debug("Detected Task: %s", task)
    logger.debug("Confidence: %s", confidence)

    updated: AgentState = {
        **state,
        "domain": domain,
        "task": task,
        "confidence": confidence,
        "intent": domain,
    }

    if needs_intent_clarification(task, confidence):
        question = build_clarification_question(state["user_query"], classification)
        updated["agent_response"] = json.dumps(
            {"status": "awaiting_input", "question": question},
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
            "task": (logistics_session or {}).get("task") or state.get("task") or "",
            "confidence": 1.0,
        }
        return _apply_classification(state, classification)

    classification = classify_domain_task(state["user_query"])
    return _apply_classification(state, classification)
