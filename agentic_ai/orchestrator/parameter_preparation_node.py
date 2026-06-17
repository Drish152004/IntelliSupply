"""Parameter preparation: validate entities, select Aura function, build payload."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from context.clarification_manager import ClarificationType
from orchestrator.hitl_session import (
    MAX_HITL_ATTEMPTS,
    STAGE_PARAMETER,
    attach_clarification_session,
    attempts_exceeded,
    build_clarification_session,
    clarification_type_for_stage,
    get_active_hitl_session,
)
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

UNRESOLVED_ENTITY_KEYS: frozenset[str] = frozenset({
    "courier_name",
    "courier_reference",
    "hub_name",
})

_SUPPORTED_TASKS: frozenset[str] = frozenset({
    "inventory_nlsql",
    "order_lookup",
    "courier_orders",
    "courier_route",
    "recent_routes",
    "delivery_days",
    "hub_route",
})

_NUMERIC_HUB_ID = re.compile(r"^\d+$")


@dataclass(frozen=True)
class PreparationResult:
    clarification_needed: bool
    function_name: str | None = None
    payload: dict[str, Any] | None = None
    question: str | None = None
    missing_fields: list[str] | None = None


def _clarification_failed_state(state: AgentState) -> AgentState:
    return {
        **state,
        "clarification_needed": False,
        "clarification_failed": True,
        "agent_response": json.dumps(
            {
                "status": "clarification_failed",
                "message": (
                    f"Unable to collect required information after "
                    f"{MAX_HITL_ATTEMPTS} attempts."
                ),
            },
            indent=2,
        ),
    }


def _hub_id_from_entities(entities: dict[str, str], role: str) -> str | None:
    """Read a resolved hub id from canonical or legacy entity keys."""
    id_key = f"{role}_hub_id"
    direct = (entities.get(id_key) or "").strip()
    if direct and _NUMERIC_HUB_ID.match(direct):
        return direct

    legacy_key = f"{role}_hub"
    legacy = (entities.get(legacy_key) or "").strip()
    if legacy and _NUMERIC_HUB_ID.match(legacy):
        return legacy
    return None


def _unresolved_entity_keys(entities: dict[str, str]) -> list[str]:
    unresolved: list[str] = []
    for key in UNRESOLVED_ENTITY_KEYS:
        value = (entities.get(key) or "").strip()
        if value:
            logger.warning(
                "Parameter preparation received unresolved entity: %s",
                key,
            )
            unresolved.append(key)
    return unresolved


def _clarification(
    *,
    question: str,
    missing_fields: list[str],
) -> PreparationResult:
    return PreparationResult(
        clarification_needed=True,
        question=question,
        missing_fields=missing_fields,
    )


def prepare_task_parameters(task: str, entities: dict[str, str]) -> PreparationResult:
    """Validate resolved entities and build function_name + payload for a task."""
    if task not in _SUPPORTED_TASKS:
        return PreparationResult(
            clarification_needed=False,
            function_name=None,
            payload={},
        )

    if task == "inventory_nlsql":
        return PreparationResult(
            clarification_needed=False,
            function_name=None,
            payload={},
        )

    unresolved = _unresolved_entity_keys(entities)
    if unresolved:
        return _clarification(
            question="Could you provide the missing details so I can continue?",
            missing_fields=unresolved,
        )

    if task == "order_lookup":
        order_id = (entities.get("order_id") or "").strip()
        if not order_id:
            return _clarification(
                question="Which order ID should I look up?",
                missing_fields=["order_id"],
            )
        return PreparationResult(
            clarification_needed=False,
            function_name="get_order_route",
            payload={"order_id": order_id},
        )

    if task == "courier_orders":
        courier_id = (entities.get("courier_id") or "").strip()
        if not courier_id:
            return _clarification(
                question="Which courier should I check orders for?",
                missing_fields=["courier_id"],
            )
        delivery_day = (entities.get("delivery_day") or "").strip()
        if delivery_day:
            return PreparationResult(
                clarification_needed=False,
                function_name="get_orders_for_courier_day",
                payload={
                    "courier_id": courier_id,
                    "delivery_day": delivery_day,
                },
            )
        return PreparationResult(
            clarification_needed=False,
            function_name="get_orders_for_courier",
            payload={"courier_id": courier_id},
        )

    if task == "courier_route":
        courier_id = (entities.get("courier_id") or "").strip()
        if not courier_id:
            return _clarification(
                question="Which courier should I use?",
                missing_fields=["courier_id"],
            )
        delivery_day = (entities.get("delivery_day") or "").strip()
        if not delivery_day:
            return _clarification(
                question="Which delivery date should I use?",
                missing_fields=["delivery_day"],
            )
        return PreparationResult(
            clarification_needed=False,
            function_name="get_saved_courier_route",
            payload={
                "courier_id": courier_id,
                "delivery_day": delivery_day,
            },
        )

    if task == "recent_routes":
        payload: dict[str, Any] = {}
        courier_id = (entities.get("courier_id") or "").strip()
        delivery_day = (entities.get("delivery_day") or "").strip()
        limit_raw = (entities.get("limit") or "").strip()
        if courier_id:
            payload["courier_id"] = courier_id
        if delivery_day:
            payload["delivery_day"] = delivery_day
        if limit_raw:
            try:
                payload["limit"] = int(limit_raw)
            except ValueError:
                payload["limit"] = limit_raw
        return PreparationResult(
            clarification_needed=False,
            function_name="get_recent_order_routes",
            payload=payload,
        )

    if task == "delivery_days":
        return PreparationResult(
            clarification_needed=False,
            function_name="list_delivery_days_with_orders",
            payload={},
        )

    if task == "hub_route":
        from_hub_id = _hub_id_from_entities(entities, "from")
        to_hub_id = _hub_id_from_entities(entities, "to")
        missing: list[str] = []
        if not from_hub_id:
            missing.append("from_hub_id")
        if not to_hub_id:
            missing.append("to_hub_id")
        if missing:
            return _clarification(
                question="Which source and destination hubs should I use?",
                missing_fields=missing,
            )
        return PreparationResult(
            clarification_needed=False,
            function_name="resolve_route_hubs",
            payload={
                "from_hub_id": from_hub_id,
                "to_hub_id": to_hub_id,
            },
        )

    return PreparationResult(clarification_needed=False, function_name=None, payload={})


def prepare_parameters(state: AgentState) -> AgentState:
    """
    Validate required entities, build execution payload, and select Aura function.

    Consumes state["task"] and resolved state["entities"] only.
    Does not classify intent or resolve entity references.
    """
    if state.get("clarification_failed"):
        return state

    task = state.get("task", "")
    entities = dict(state.get("entities") or {})

    updated: AgentState = {
        **state,
        "entities": entities,
        "clarification_needed": False,
        "missing_required_parameters": False,
        "clarification_type": None,
        "clarification_question": None,
        "missing_fields": [],
        "function_name": None,
        "payload": {},
    }

    result = prepare_task_parameters(task, entities)

    if not result.clarification_needed:
        return {
            **updated,
            "function_name": result.function_name,
            "payload": result.payload or {},
        }

    active_session = get_active_hitl_session(state)
    if attempts_exceeded(active_session):
        logger.info("Parameter clarification attempt limit reached for task=%s", task)
        return {
            **_clarification_failed_state(updated),
            "missing_required_parameters": True,
            "missing_fields": result.missing_fields or [],
        }

    agent_response = json.dumps(
        {
            "status": "awaiting_input",
            "clarification_type": ClarificationType.ENTITY.value,
            "question": result.question,
            "missing_entities": result.missing_fields,
        },
        indent=2,
    )
    session = build_clarification_session(
        updated,
        stage=STAGE_PARAMETER,
        clarification_type=clarification_type_for_stage(STAGE_PARAMETER),
        base_session=active_session,
    )
    patched = attach_clarification_session(updated, session, stage=STAGE_PARAMETER)
    return {
        **patched,
        "missing_required_parameters": True,
        "clarification_needed": True,
        "clarification_stage": STAGE_PARAMETER,
        "clarification_type": ClarificationType.ENTITY.value,
        "clarification_question": result.question,
        "missing_fields": result.missing_fields or [],
        "agent_response": agent_response,
    }
