"""Orchestrator node for production ML execution (Phase 6B)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from orchestrator.resource_rbac import authorize_courier_resource
from orchestrator.state import AgentState

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.ml_executor import get_ml_executor  # noqa: E402

logger = logging.getLogger(__name__)


def execute_ml(state: AgentState) -> AgentState:
    """
    Execute the production ML pipeline when context resolution is complete.

    Skips execution when ready_for_ml is False (clarification still required).
    """
    if not state.get("ready_for_ml"):
        return state

    allowed, reason, entities = authorize_courier_resource(state)
    if not allowed:
        return {
            **state,
            "entities": entities,
            "authorization_denied": True,
            "execution_status": "error",
            "execution_error": reason,
            "agent_response": _error_response(reason or "Access denied", task=state.get("task", "")),
        }

    task = state.get("task", "")
    payload = state.get("payload")
    if not task or not payload:
        return {
            **state,
            "execution_status": "error",
            "execution_error": "Missing task or payload for ML execution",
            "agent_response": _error_response(
                "ML execution skipped: missing task or payload",
                task=task,
            ),
        }

    outcome = get_ml_executor().execute(task, payload)
    update: dict[str, Any] = {
        **state,
        **outcome.to_state_fields(),
        "agent_response": outcome.to_agent_response(task=task),
    }
    return update  # type: ignore[return-value]


def _error_response(message: str, *, task: str) -> str:
    import json

    return json.dumps(
        {
            "status": "error",
            "stage": "ml_execution",
            "message": message,
            "task": task,
        },
        indent=2,
    )
