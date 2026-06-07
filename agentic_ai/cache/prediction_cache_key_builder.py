"""Deterministic cache keys for ML prediction results using business identifiers."""

from __future__ import annotations

import re
from typing import Any

from orchestrator.state import AgentState


def _normalize_token(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned.upper()


class PredictionCacheKeyBuilder:
    """Build prediction cache keys from resolved entities and payloads — not raw queries."""

    @staticmethod
    def build(task: str, *, entities: dict[str, str], payload: dict[str, Any] | None = None) -> str | None:
        payload = payload or {}

        if task == "eta_prediction":
            order_id = entities.get("order_id") or payload.get("order_id")
            if not order_id:
                return None
            return f"eta_prediction:{_normalize_token(str(order_id))}"

        if task == "route_prediction":
            order_id = entities.get("order_id") or payload.get("order_id")
            if not order_id:
                return None
            return f"route_prediction:{_normalize_token(str(order_id))}"

        if task == "demand_forecast":
            city = (
                entities.get("city")
                or entities.get("city_name")
                or payload.get("city")
            )
            horizon = entities.get("horizon") or payload.get("horizon")
            if not city or horizon is None or str(horizon).strip() == "":
                return None
            return f"demand_forecast:{_normalize_token(str(city))}:{str(horizon).strip()}"

        return None

    @staticmethod
    def build_from_state(state: AgentState) -> str | None:
        """Build a prediction cache key from orchestrator state after context resolution."""
        task = state.get("task", "")
        entities = dict(state.get("entities") or {})
        payload = state.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        return PredictionCacheKeyBuilder.build(task, entities=entities, payload=payload)
