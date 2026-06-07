"""
Unified response formatting for all orchestrator terminal paths.

Normalizes graph hits, ML predictions, clarifications, RBAC denials, errors,
and agent outputs into a consistent schema for the frontend.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from orchestrator.rbac.session_context import build_session_for_response
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_GRAPH_MESSAGES: dict[str, str] = {
    "eta_lookup": "ETA retrieved from knowledge graph",
    "shipment_lookup": "Shipment details retrieved from knowledge graph",
    "courier_lookup": "Courier details retrieved from knowledge graph",
    "route_lookup": "Route retrieved from knowledge graph",
}

_PREDICTION_MESSAGES: dict[str, str] = {
    "eta": "ETA prediction generated successfully",
    "route": "Route prediction generated successfully",
    "demand_forecast": "Demand forecast generated successfully",
}


class ResponseFormatter:
    """Build a unified API response from orchestrator state."""

    def format(self, state: AgentState) -> dict[str, Any]:
        if state.get("access_denied"):
            return self._format_access_denied(state)

        if state.get("authorization_denied"):
            return self._format_graph_access_denied(state)

        if state.get("execution_status") == "error":
            return self._format_execution_error(state)

        if state.get("clarification_needed"):
            return self._format_clarification(state)

        if state.get("graph_hit"):
            return self._format_graph(state)

        if state.get("prediction_cache_hit"):
            return self._format_prediction_cache(state)

        if state.get("execution_status") == "success" and state.get("prediction_result") is not None:
            return self._format_prediction(state)

        if state.get("cache_hit"):
            return self._format_cache(state)

        raw = self._parse_agent_response(state.get("agent_response", ""))
        if raw:
            return self._format_from_agent_payload(state, raw)

        return self._format_generic_error(
            stage="response_format",
            message="Unable to determine response type",
            details={"task": state.get("task", "")},
        )

    def serialize(self, state: AgentState) -> str:
        return json.dumps(self.format(state), indent=2, default=str)

    @staticmethod
    def _parse_agent_response(agent_response: str) -> dict[str, Any] | None:
        if not agent_response or not agent_response.strip():
            return None
        try:
            payload = json.loads(agent_response)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _format_access_denied(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", ""))
        role = state.get("user_role", "")
        task = state.get("task", "")
        message = (raw or {}).get("reason", f"Role {role} is not allowed to execute {task}")
        return {
            "status": "access_denied",
            "message": message,
            "role": role,
            "task": task,
        }

    def _format_graph_access_denied(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", "")) or {}
        role = state.get("user_role", "")
        task = state.get("task", "")
        return {
            "status": "access_denied",
            "message": raw.get("reason", "Not authorized to access this graph resource"),
            "role": role,
            "task": task,
        }

    def _format_execution_error(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", "")) or {}
        task = state.get("task", "")
        return {
            "status": "error",
            "stage": raw.get("stage", "ml_execution"),
            "message": state.get("execution_error") or raw.get("message", "Model execution failed"),
            "details": {
                "task": task,
                **({"duration_ms": state.get("model_execution_time_ms")} if state.get("model_execution_time_ms") else {}),
            },
        }

    def _format_clarification(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", "")) or {}
        missing = state.get("missing_fields") or []
        if not missing:
            missing = raw.get("missing_fields") or raw.get("missing_entities") or []

        clarification_type = (
            state.get("clarification_type")
            or raw.get("clarification_type")
            or "ENTITY"
        )
        question = (
            state.get("clarification_question")
            or raw.get("question")
            or "Additional information is required to continue."
        )

        response: dict[str, Any] = {
            "status": "clarification_required",
            "clarification_type": clarification_type,
            "question": question,
            "missing_fields": list(missing),
        }
        session = build_session_for_response(state)
        if session:
            response["data"] = {"session": session}
        return response

    def _format_graph(self, state: AgentState) -> dict[str, Any]:
        task = state.get("task", "")
        data = state.get("graph_result")
        if data is None:
            raw = self._parse_agent_response(state.get("agent_response", "")) or {}
            data = raw.get("result", {})

        message = _GRAPH_MESSAGES.get(task, "Result retrieved from knowledge graph")
        return {
            "status": "success",
            "source": "graph",
            "task": task,
            "message": message,
            "data": data or {},
        }

    def _format_prediction_cache(self, state: AgentState) -> dict[str, Any]:
        task = state.get("task", "")
        cached = state.get("cached_prediction_result") or {}
        prediction_type = cached.get("prediction_type") or state.get("prediction_type", "")
        message = _PREDICTION_MESSAGES.get(
            prediction_type,
            "Cached prediction returned",
        )
        data: dict[str, Any] = dict(cached.get("result") or state.get("prediction_result") or {})
        model_name = cached.get("model_name") or state.get("model_name")
        if model_name:
            data["model_name"] = model_name
        if prediction_type:
            data["prediction_type"] = prediction_type

        return {
            "status": "success",
            "source": "cache",
            "task": task,
            "message": message,
            "data": data,
        }

    def _format_prediction(self, state: AgentState) -> dict[str, Any]:
        task = state.get("task", "")
        prediction_type = state.get("prediction_type", "")
        message = _PREDICTION_MESSAGES.get(
            prediction_type,
            "Prediction generated successfully",
        )
        data: dict[str, Any] = dict(state.get("prediction_result") or {})
        if state.get("model_name"):
            data["model_name"] = state["model_name"]
        if state.get("model_execution_time_ms") is not None:
            data["duration_ms"] = state["model_execution_time_ms"]
        if prediction_type:
            data["prediction_type"] = prediction_type

        return {
            "status": "success",
            "source": "ml",
            "task": task,
            "message": message,
            "data": data,
        }

    def _format_cache(self, state: AgentState) -> dict[str, Any]:
        task = state.get("task", "")
        raw = self._parse_agent_response(state.get("agent_response", "")) or {}
        data = state.get("cached_result") or raw.get("result") or {}
        return {
            "status": "success",
            "source": "cache",
            "task": task,
            "message": "Cached result returned",
            "data": data,
        }

    def _format_from_agent_payload(
        self,
        state: AgentState,
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        status = raw.get("status", "")
        task = state.get("task", "")
        agent = raw.get("agent", state.get("domain", ""))

        if status == "denied":
            return {
                "status": "access_denied",
                "message": raw.get("reason", "Access denied"),
                "role": state.get("user_role", ""),
                "task": task,
            }

        if status in {"awaiting_input", "ready_for_ml"} or raw.get("needs_clarification"):
            missing = raw.get("missing_fields") or raw.get("missing_entities") or []
            clarification: dict[str, Any] = {
                "status": "clarification_required",
                "clarification_type": raw.get("clarification_type", "ENTITY"),
                "question": raw.get("question", "Additional information is required."),
                "missing_fields": list(missing),
            }
            session = build_session_for_response(state)
            if session:
                clarification["data"] = {"session": session}
            return clarification

        if status == "error":
            return {
                "status": "error",
                "stage": raw.get("stage", "unknown"),
                "message": raw.get("message", "An error occurred"),
                "details": {k: v for k, v in raw.items() if k not in {"status", "stage", "message"}},
            }

        if raw.get("graph_hit") and raw.get("result"):
            return {
                "status": "success",
                "source": "graph",
                "task": task,
                "message": _GRAPH_MESSAGES.get(task, "Result retrieved from knowledge graph"),
                "data": raw["result"],
            }

        if status == "prediction_complete" or raw.get("prediction_type"):
            prediction_type = raw.get("prediction_type", state.get("prediction_type", ""))
            return {
                "status": "success",
                "source": "ml",
                "task": task,
                "message": _PREDICTION_MESSAGES.get(prediction_type, "Prediction generated successfully"),
                "data": raw.get("result", {}),
            }

        if agent == "inventory" or state.get("domain") == "inventory":
            return self._format_inventory(state, raw)

        if status == "complete":
            data: dict[str, Any] = {}
            if raw.get("answer"):
                data["answer"] = raw["answer"]
            if raw.get("result"):
                data["result"] = raw["result"]
            if raw.get("business_result"):
                data["business_result"] = raw["business_result"]
            if raw.get("session") is not None:
                data["session"] = raw["session"]

            source = "inventory" if agent == "inventory" else "agent"
            message = raw.get("answer") or "Request completed successfully"
            return {
                "status": "success",
                "source": source,
                "task": task,
                "message": message,
                "data": data,
            }

        return self._format_generic_error(
            stage="response_format",
            message="Unrecognized agent response format",
            details={"task": task, "raw_status": status},
        )

    def _format_inventory(self, state: AgentState, raw: dict[str, Any]) -> dict[str, Any]:
        task = state.get("task", "inventory_nlsql")
        status = raw.get("status", "")

        if status == "awaiting_input":
            inventory_clarification: dict[str, Any] = {
                "status": "clarification_required",
                "clarification_type": "PAYLOAD",
                "question": raw.get("question", "Additional inventory details are required."),
                "missing_fields": list(raw.get("missing_fields") or []),
            }
            session = build_session_for_response(state)
            if session:
                inventory_clarification["data"] = {"session": session}
            return inventory_clarification

        data: dict[str, Any] = {}
        if raw.get("answer"):
            data["answer"] = raw["answer"]
        if raw.get("session") is not None:
            data["session"] = raw["session"]
        if raw.get("result"):
            data["result"] = raw["result"]
        if raw.get("business_result"):
            data["business_result"] = raw["business_result"]

        return {
            "status": "success",
            "source": "inventory",
            "task": task,
            "message": raw.get("answer") or "Inventory request completed successfully",
            "data": data,
        }

    @staticmethod
    def _format_generic_error(
        *,
        stage: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "error",
            "stage": stage,
            "message": message,
            "details": details or {},
        }


def format_response(state: AgentState) -> AgentState:
    """LangGraph node: normalize state into a unified final response."""
    logger.info("RESPONSE FORMAT START")
    formatter = ResponseFormatter()
    formatted = formatter.format(state)
    final_response = formatter.serialize(state)
    logger.info(
        "RESPONSE FORMAT COMPLETE\nstatus=%s\nsource=%s",
        formatted.get("status"),
        formatted.get("source", ""),
    )
    return {**state, "final_response": final_response}
