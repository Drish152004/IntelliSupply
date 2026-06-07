"""FastAPI routes for testing the IntelliSupply Copilot orchestrator."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter

from .schemas import CopilotRequest
from orchestrator.graph import run_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["copilot"])


def _parse_final_response(final_response: str) -> Any:
    """Deserialize orchestrator final_response JSON without reformatting."""
    try:
        return json.loads(final_response)
    except (json.JSONDecodeError, TypeError):
        return final_response


def _invoke_orchestrator(body: CopilotRequest) -> dict[str, Any]:
    return run_orchestrator(
        body.query,
        logistics_session=body.logistics_session,
        authenticated_user=body.authenticated_user,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.post("/query")
def query(body: CopilotRequest) -> Any:
    try:
        result = _invoke_orchestrator(body)
        return _parse_final_response(result["final_response"])
    except Exception as exc:
        logger.exception("Copilot query failed")
        return {"status": "error", "message": str(exc)}


@router.post("/debug")
def debug(body: CopilotRequest) -> dict[str, Any]:
    try:
        result = _invoke_orchestrator(body)
        return {
            "intent": result.get("intent"),
            "task": result.get("task"),
            "cache_hit": result.get("cache_hit", False),
            "graph_hit": result.get("graph_hit", False),
            "ready_for_ml": result.get("ready_for_ml", False),
            "prediction_result": result.get("prediction_result"),
            "final_response": _parse_final_response(result.get("final_response", "")),
        }
    except Exception as exc:
        logger.exception("Copilot debug failed")
        return {"status": "error", "message": str(exc)}
