"""
Orchestration tracing utilities for LangGraph workflow execution.

Provides node wrappers, state-diff logging, routing logs, structured JSON
observability events, and run-level start/end summaries written to
``agentic_ai/app.log``.
"""

from __future__ import annotations

import contextvars
import functools
import json
import logging
import time
import traceback
import uuid
from collections.abc import Callable
from typing import Any, Protocol

from logging_config import setup_trace_logging
from observability.node_payloads import extract_node_input, extract_node_output
from observability.redaction import MAX_VALUE_LEN, is_sensitive_key, redact_value
from observability.trace_events import (
    get_current_trace_id,
    set_current_trace_id,
    trace_node_input,
    trace_node_output,
)
from orchestrator.state import AgentState

setup_trace_logging()

logger = logging.getLogger("trace")

_execution_path_var: contextvars.ContextVar[list[str]] = contextvars.ContextVar(
    "execution_path", default=[]
)
_last_node_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("last_node", default=None)


def generate_trace_id() -> str:
    """Return a short unique trace identifier for a single orchestration run."""
    return uuid.uuid4().hex[:6]


def _trace_log(trace_id: str, message: str, *, level: int = logging.INFO) -> None:
    """Emit a trace log line with the required ``[trace=<id>]`` prefix."""
    for line in message.splitlines():
        logger.log(level, "[trace=%s] %s", trace_id, line)


def _safe_repr(value: Any) -> str:
    if value is None:
        return "None"
    try:
        if isinstance(value, (dict, list, tuple)):
            text = json.dumps(redact_value("value", value), default=str, ensure_ascii=False)
        else:
            text = repr(value)
    except Exception:
        text = f"<{type(value).__name__}>"

    if len(text) > MAX_VALUE_LEN:
        return text[:MAX_VALUE_LEN] + "..."
    return text


def _format_diff(old: Any, new: Any, prefix: str = "") -> list[str]:
    if isinstance(old, dict) and isinstance(new, dict):
        lines: list[str] = []
        for key in sorted(set(old) | set(new)):
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val == new_val:
                continue
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if is_sensitive_key(key_path):
                lines.append(f"{key_path}: <redacted> -> <redacted>")
                continue
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                lines.extend(_format_diff(old_val, new_val, key_path))
            else:
                lines.append(f"{key_path}: {_safe_repr(old_val)} -> {_safe_repr(new_val)}")
        return lines

    if old != new:
        label = prefix or "value"
        return [f"{label}: {_safe_repr(old)} -> {_safe_repr(new)}"]
    return []


def log_state_diff(trace_id: str, before: dict[str, Any], after: dict[str, Any]) -> None:
    """Log only keys whose values changed between two state snapshots."""
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if old == new:
            continue
        if is_sensitive_key(key):
            _trace_log(trace_id, f"{key} changed: <redacted>")
            continue
        if isinstance(old, dict) and isinstance(new, dict):
            lines = _format_diff(old, new, prefix=str(key))
        else:
            lines = [f"{key}: {_safe_repr(old)} -> {_safe_repr(new)}"]
        if lines:
            _trace_log(trace_id, f"{key} changed:\n" + "\n".join(lines))


def _record_node(node_name: str) -> None:
    path = list(_execution_path_var.get() or [])
    path.append(node_name)
    _execution_path_var.set(path)
    _last_node_var.set(node_name)


def begin_trace(trace_id: str, state: AgentState) -> None:
    """Initialize per-run trace context and log RUN START."""
    set_current_trace_id(trace_id)
    _execution_path_var.set([])
    _last_node_var.set(None)
    query = _safe_repr(state.get("user_query", ""))
    role = state.get("user_role") or ""
    _trace_log(trace_id, f'RUN START\nquery={query}\nrole="{role}"')


def end_trace(trace_id: str, result: AgentState, run_start: float) -> None:
    """Log RUN END with summary fields and the full execution path."""
    duration_ms = int((time.perf_counter() - run_start) * 1000)
    path = _execution_path_var.get() or []
    last_node = _last_node_var.get() or "unknown"
    authorized = not (result.get("authorization_denied") or result.get("access_denied"))
    path_text = " -> ".join(path) if path else "none"
    _trace_log(
        trace_id,
        (
            "RUN END\n"
            f"task={result.get('task', '')}\n"
            f"authorized={authorized}\n"
            f"duration_ms={duration_ms}\n"
            f"final_node={last_node}\n"
            f"path={path_text}"
        ),
    )


def log_route(trace_id: str, current_node: str, next_node: str, reason: str) -> None:
    """Log a conditional routing decision."""
    _trace_log(trace_id, f"ROUTE {current_node} -> {next_node}\nreason={reason}")


def log_entity_resolution(
    trace_id: str,
    *,
    entity_type: str,
    entity_key: str,
    before: str,
    after: str | None,
    status: str,
) -> None:
    """
    Log a human-readable entity resolution line for courier or hub lookups.

    status is one of: success, failure, unchanged.
    """
    if status == "success":
        _trace_log(
            trace_id,
            f"Resolved {entity_type} ({entity_key}):\n{before}\n→\n{after}",
        )
        return
    if status == "unchanged":
        _trace_log(trace_id, f"{entity_type} ({entity_key}) already canonical: {before}")
        return
    _trace_log(
        trace_id,
        f"{entity_type} resolution failed ({entity_key}): {before}",
        level=logging.WARNING,
    )


def log_identity_binding(
    trace_id: str,
    *,
    bound_courier_name: str | None,
    bound_courier_id: str | None,
    source: str,
    normalized_name: str | None = None,
) -> None:
    """Log a human-readable courier identity binding line.

    source is one of: name_resolution, authenticated_fallback, unresolved.
    normalized_name is the numeric form a worded JWT name was mapped to, if any.
    """
    normalized_line = (
        f"normalized_name={normalized_name}\n" if normalized_name else ""
    )
    if bound_courier_id:
        _trace_log(
            trace_id,
            (
                "Courier identity bound:\n"
                f"bound_courier_name={bound_courier_name}\n"
                f"{normalized_line}"
                f"→\nbound_courier_id={bound_courier_id}\n"
                f"source={source}"
            ),
        )
        return
    _trace_log(
        trace_id,
        (
            "Courier identity unbound: "
            f"bound_courier_name={bound_courier_name} "
            f"normalized_name={normalized_name} (source={source})"
        ),
        level=logging.WARNING,
    )


def log_authz_allow(trace_id: str, *, task: str, bound_courier_id: str | None) -> None:
    """Log a successful courier resource ownership check."""
    _trace_log(
        trace_id,
        f"AUTHZ_ALLOW\ntask={task}\nbound_courier_id={bound_courier_id}",
    )


def log_authz_deny(
    trace_id: str,
    *,
    task: str,
    bound_courier_id: str | None,
    requested_courier_id: str | None,
) -> None:
    """Log a denied courier resource ownership check (courier_id mismatch)."""
    _trace_log(
        trace_id,
        (
            "AUTHZ_DENY\n"
            f"task={task}\n"
            f"bound_courier_id={bound_courier_id}\n"
            f"requested_courier_id={requested_courier_id}"
        ),
        level=logging.WARNING,
    )


def log_authz_deny_order(
    trace_id: str,
    *,
    order_id: str,
    assigned_courier_id: str | None,
    bound_courier_id: str | None,
) -> None:
    """Log a denied courier order ownership check (order not assigned to courier)."""
    _trace_log(
        trace_id,
        (
            "AUTHZ_DENY_ORDER\n"
            f"order_id={order_id}\n"
            f"assigned_courier_id={assigned_courier_id}\n"
            f"bound_courier_id={bound_courier_id}"
        ),
        level=logging.WARNING,
    )


def _resolve_trace_id(state: AgentState) -> str:
    return state.get("trace_id") or get_current_trace_id() or "unknown"


class _StateNodeCallable(Protocol):
    """Structural type matching LangGraph's ``StateNode`` (keyword ``state`` arg).

    ``Callable[[AgentState], AgentState]`` declares a positional-only parameter,
    which does not satisfy LangGraph's node protocol (``def __call__(self,
    state)``). Returning this protocol keeps ``add_node`` type-clean without
    altering node behavior.
    """

    def __call__(self, state: AgentState) -> AgentState: ...


def traced_node(
    node_name: str, fn: Callable[[AgentState], AgentState]
) -> _StateNodeCallable:
    """Wrap a graph node with entry/exit, state-diff, and error tracing."""

    @functools.wraps(fn)
    def wrapper(state: AgentState) -> AgentState:
        trace_id = _resolve_trace_id(state)
        set_current_trace_id(trace_id)
        before = dict(state)
        _trace_log(trace_id, f"ENTER {node_name}")
        trace_node_input(
            node_name,
            extract_node_input(node_name, state),
            trace_id=trace_id,
            state=before,
        )
        start = time.perf_counter()
        try:
            result = fn(state)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            log_state_diff(trace_id, before, dict(result))
            trace_node_output(
                node_name,
                extract_node_output(node_name, before, result),
                trace_id=trace_id,
                state=dict(result),
            )
            _trace_log(trace_id, f"EXIT {node_name} ({elapsed_ms}ms)")
            _record_node(node_name)
            return result
        except Exception as exc:
            _trace_log(
                trace_id,
                f"ERROR {node_name}\n{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                level=logging.ERROR,
            )
            raise

    return wrapper


def _route_reason(current_node: str, state: AgentState, next_node: str) -> str:
    if current_node == "coarse_authorization":
        if next_node == "response_formatter":
            if state.get("clarification_needed"):
                return "clarification_needed"
            return "access_denied"
        return "authorized"
    if current_node == "entity_extraction":
        return "entities_extracted"
    if current_node == "response_formatter":
        return "terminal"
    if current_node == "intent":
        if next_node == "response_formatter":
            if state.get("clarification_needed"):
                return "clarification_needed"
            return "intent_clarification_needed"
        return "intent_resolved"
    if current_node == "entity_resolution":
        return "entities_resolved"
    if current_node == "parameter_preparation":
        if next_node == "response_formatter":
            return "clarification_needed"
        return "parameters_prepared"
    return "unknown"


def traced_route(
    current_node: str, route_fn: Callable[[AgentState], str]
) -> Callable[[AgentState], str]:
    """Wrap a conditional routing function with ROUTE logging."""

    @functools.wraps(route_fn)
    def wrapper(state: AgentState) -> str:
        next_node = route_fn(state)
        trace_id = _resolve_trace_id(state)
        reason = _route_reason(current_node, state, next_node)
        log_route(trace_id, current_node, next_node, reason)
        return next_node

    return wrapper
