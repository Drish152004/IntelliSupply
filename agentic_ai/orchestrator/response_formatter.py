"""
Unified response formatting for all orchestrator terminal paths.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from context.clarification_manager import ClarificationType
from orchestrator.answer_generation import generate_answer
from orchestrator.result_normalizer import normalize_result_for_answer
from orchestrator.hitl_session import (
    STAGE_DOMAIN,
    clear_all_hitl_sessions,
    should_clear_hitl_sessions,
)
from orchestrator.rbac.session_context import build_session_for_response
from orchestrator.response_synthesis import synthesize_answer
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_UNAVAILABLE_MESSAGE = "That information isn't currently available."
_EMPTY_RESULT_MESSAGE = "No matching records were found."

_GRAPH_MESSAGES: dict[str, str] = {
    "order_lookup": "Order details retrieved from knowledge graph",
    "courier_orders": "Courier orders retrieved from knowledge graph",
    "courier_route": "Courier route retrieved from knowledge graph",
    "recent_routes": "Recent deliveries retrieved from knowledge graph",
    "delivery_days": "Delivery schedules retrieved from knowledge graph",
    "hub_route": "Hub route retrieved from knowledge graph",
    "inventory_nlsql": "Inventory query completed",
}


class ResponseFormatter:
    """Build a unified API response from orchestrator state."""

    def format(self, state: AgentState) -> dict[str, Any]:
        if state.get("clarification_failed"):
            return self._format_clarification_failed(state)

        if state.get("authorization_denied"):
            return self._format_authorization_denied(state)

        if state.get("access_denied"):
            return self._format_access_denied(state)

        if state.get("clarification_needed"):
            return self._format_clarification(state)

        if state.get("execution_status") == "error":
            return self._format_execution_error(state)

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

    def _format_clarification_failed(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", "")) or {}
        return {
            "status": "clarification_failed",
            "message": raw.get(
                "message",
                "Unable to collect required information. Please start a new request.",
            ),
        }

    def _format_authorization_denied(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", ""))
        role = state.get("user_role", "")
        task = state.get("task", "")
        message = (raw or {}).get("reason", f"Role {role} is not authorized for {task}")
        return {
            "status": "authorization_denied",
            "clarification_type": ClarificationType.AUTHORIZATION.value,
            "message": message,
            "role": role,
            "task": task,
        }

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

    def _format_execution_error(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", "")) or {}
        return {
            "status": "error",
            "stage": raw.get("stage", "rag_execution"),
            "message": state.get("execution_error") or raw.get("message") or _UNAVAILABLE_MESSAGE,
            "details": {"task": state.get("task", "")},
        }

    def _format_clarification(self, state: AgentState) -> dict[str, Any]:
        raw = self._parse_agent_response(state.get("agent_response", "")) or {}
        missing = state.get("missing_fields") or raw.get("missing_entities") or []
        clarification_type = state.get("clarification_type") or raw.get("clarification_type") or "INTENT"
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
            data: dict[str, Any] = {"session": session}
            if state.get("clarification_stage") == STAGE_DOMAIN or session.get(
                "clarification_stage"
            ) == STAGE_DOMAIN:
                data["pending_clarification_session"] = session
            response["data"] = data
        return response

    def _format_from_agent_payload(
        self,
        state: AgentState,
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        status = raw.get("status", "")
        task = state.get("task", "")
        domain = state.get("domain", raw.get("domain", ""))

        if status == "denied":
            return {
                "status": "access_denied",
                "message": raw.get("reason", "Access denied"),
                "role": state.get("user_role", ""),
                "task": task,
            }

        if status == "awaiting_input" or raw.get("needs_clarification"):
            missing = raw.get("missing_fields") or raw.get("missing_entities") or []
            clarification: dict[str, Any] = {
                "status": "clarification_required",
                "clarification_type": raw.get("clarification_type", "ENTITY"),
                "question": raw.get("question", "Additional information is required."),
                "missing_fields": list(missing),
            }
            session = build_session_for_response(state)
            if session:
                data: dict[str, Any] = {"session": session}
                if session.get("clarification_stage") == STAGE_DOMAIN:
                    data["pending_clarification_session"] = session
                clarification["data"] = data
            return clarification

        if status == "error":
            return {
                "status": "error",
                "stage": raw.get("stage", "unknown"),
                "message": raw.get("message", "An error occurred"),
                "details": {k: v for k, v in raw.items() if k not in {"status", "stage", "message"}},
            }

        if status in {"complete", "success"}:
            source = "inventory" if domain == "inventory" else "graph"

            if source == "graph":
                return self._format_graph_success(state, raw, task)

            result = raw.get("result") or {}
            answer = raw.get("answer") or result.get("answer") or "Request completed successfully"
            data: dict[str, Any] = {"answer": answer}
            if isinstance(result, dict):
                data.update({k: v for k, v in result.items() if k != "answer"})

            return {
                "status": "success",
                "source": "inventory",
                "task": task,
                "message": _GRAPH_MESSAGES.get(task, answer),
                "data": data,
            }

        return self._format_generic_error(
            stage="response_format",
            message="Unrecognized agent response format",
            details={"task": task, "raw_status": status},
        )

    def _format_graph_success(
        self,
        state: AgentState,
        raw: dict[str, Any],
        task: str,
    ) -> dict[str, Any]:
        """Preserve the full Aura Bridge payload and generate the answer.

        The raw GraphDB result is kept intact under ``data.graph_result`` so
        no fields are dropped or flattened. The human-readable answer is
        produced by the LLM answer layer from ``user_query`` + ``task`` +
        ``domain`` + raw graph rows. Empty results are answered deterministically
        without an LLM call; the rule-based synthesizer is the fallback whenever
        the LLM call fails, parses badly, or returns an empty answer.
        """
        graph_result = raw.get("graph_result")
        if graph_result is None:
            graph_result = raw.get("result") or {}

        graph_data = graph_result.get("data") if isinstance(graph_result, dict) else None
        has_data = graph_data not in (None, [], {}, "")

        if not has_data:
            answer = _EMPTY_RESULT_MESSAGE
            message = answer
        else:
            answer = self._generate_graph_answer(state, task, graph_result, graph_data)
            message = _GRAPH_MESSAGES.get(task, answer)

        return {
            "status": "success",
            "source": "graph",
            "task": task,
            "message": message,
            "data": {
                "graph_result": graph_result,
                "answer": answer,
            },
        }

    @staticmethod
    def _generate_graph_answer(
        state: AgentState,
        task: str,
        graph_result: dict[str, Any] | Any,
        graph_data: Any,
    ) -> str:
        """LLM answer with a rule-based fallback.

        Only the result rows reach the LLM: cypher/sql, prompts, and execution
        metadata are never forwarded. On any LLM failure (exception, unparseable
        output, or empty answer) this falls back to the existing synthesizer.
        """
        user_query = state.get("user_query", "")
        domain = state.get("domain") or "logistics"

        # Normalize raw rows into analyst-ready data immediately before the
        # answer model. Only the LLM input is reshaped; the original raw
        # graph_data is preserved by the caller and used by the fallback.
        normalized = normalize_result_for_answer(graph_data)

        answer = generate_answer(
            user_query=user_query,
            task=task,
            domain=domain,
            result=normalized,
            count=normalized.get("total_records"),
        )
        if answer:
            logger.info("answer_llm_success task=%s domain=%s", task, domain)
            return answer

        logger.info("answer_llm_fallback task=%s domain=%s", task, domain)
        return synthesize_answer(user_query, task, graph_data)

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
    """LangGraph node: normalize state into a unified final response.

    On a semantic cache hit the cached response is returned verbatim as
    ``final_response`` and all formatting logic is bypassed.
    """
    if state.get("cache_hit") and state.get("cache_response") is not None:
        logger.info("RESPONSE FORMAT served from semantic cache")
        return {**state, "final_response": state["cache_response"]}

    formatter = ResponseFormatter()
    formatted = formatter.format(state)
    updated_state: AgentState = dict(state)
    if should_clear_hitl_sessions(formatted.get("status")):
        updated_state = clear_all_hitl_sessions(updated_state)
    final_response = formatter.serialize(updated_state)
    logger.info(
        "RESPONSE FORMAT COMPLETE status=%s source=%s",
        formatted.get("status"),
        formatted.get("source", ""),
    )
    return {**updated_state, "final_response": final_response}
