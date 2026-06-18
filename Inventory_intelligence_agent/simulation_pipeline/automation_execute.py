from __future__ import annotations

from dataclasses import fields
from typing import Any

from decision_models import Decision, DecisionType
from scenario_models import ScenarioPatch
from state_models import (
    DemandState,
    EventState,
    ForecastState,
    InventoryState,
    ReplenishmentState,
    RiskState,
    ScenarioState,
)


def _build_dataclass(cls, payload: dict[str, Any]):
    field_names = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in payload.items() if key in field_names})


def decision_from_payload(payload: dict[str, Any]) -> Decision:
    return Decision(
        decision_id=str(payload["decision_id"]),
        decision_type=DecisionType(str(payload["decision_type"])),
        title=str(payload.get("title") or ""),
        rationale=str(payload.get("rationale") or ""),
        parameters=dict(payload.get("parameters") or {}),
    )


def scenario_from_payload(payload: dict[str, Any]) -> ScenarioState:
    patch_payload = payload.get("applied_patch")
    applied_patch = (
        ScenarioPatch.model_validate(patch_payload)
        if patch_payload is not None
        else ScenarioPatch()
    )

    return ScenarioState(
        hub_id=str(payload["hub_id"]),
        product_id=str(payload["product_id"]),
        category=str(payload["category"]),
        simulation_date=str(payload["simulation_date"]),
        planning_window_days=int(payload.get("planning_window_days") or 7),
        inventory=_build_dataclass(InventoryState, payload["inventory"]),
        demand=_build_dataclass(DemandState, payload["demand"]),
        forecast=_build_dataclass(ForecastState, payload["forecast"]),
        event=_build_dataclass(EventState, payload["event"]),
        replenishment=_build_dataclass(ReplenishmentState, payload["replenishment"]),
        risk=_build_dataclass(RiskState, payload["risk"]),
        applied_patch=applied_patch,
    )
