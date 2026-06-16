"""Inventory planning and simulation API routes."""

from __future__ import annotations

import enum
import math
from dataclasses import fields, is_dataclass
from typing import Annotated, Any, List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies.auth import TokenUser, require_roles

from scenario_models import ScenarioPatch
from recommendation_models import PlanningPipelineConfig
from base_state import build_base_state
from planning_pipeline import run_full_planning_pipeline
from scenario_understanding_agent import understand_scenario

router = APIRouter(prefix="/planning", tags=["planning"])

PlanningUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "inventory_manager", "logistics_manager")),
]


def _to_jsonable(obj: Any) -> Any:
    if obj is None:
        return None

    if isinstance(obj, (str, bool)):
        return obj

    if isinstance(obj, enum.Enum):
        return obj.value

    if isinstance(obj, BaseModel):
        return _to_jsonable(obj.model_dump())

    if isinstance(obj, np.generic):
        value = obj.item()
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value

    if isinstance(obj, np.ndarray):
        return [_to_jsonable(v) for v in obj.tolist()]

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, int):
        return obj

    if is_dataclass(obj) and not isinstance(obj, type):
        return {
            field.name: _to_jsonable(getattr(obj, field.name))
            for field in fields(obj)
        }

    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]

    return obj


class EntityScopeRequest(BaseModel):
    hub_id: str
    product_id: str
    category: str
    simulation_date: str


class UnderstandScenarioRequest(EntityScopeRequest):
    scenario_query: str = Field(..., min_length=1)


class SimulateRequest(EntityScopeRequest):
    scenario_query: Optional[str] = None
    patch: Optional[ScenarioPatch] = None
    planning_window_days: int = Field(default=7, ge=1, le=30)
    n_worlds: int = 100
    random_seed: Optional[int] = 42
    skip_llm: bool = False
    auto_select_all_decisions: bool = True
    selected_decision_ids: Optional[List[str]] = None


def _load_context_data() -> dict[str, Any]:
    import pandas as pd
    from base_state import DATA_DIR

    df = pd.read_csv(
        DATA_DIR / "demand_forecast_daily.csv",
        usecols=["hub_id", "product_id", "category", "forecast_date"],
    )

    hubs = sorted(int(h) for h in df["hub_id"].unique())
    products = sorted(df["product_id"].unique().tolist())
    categories = sorted(df["category"].unique().tolist())
    dates = sorted(df["forecast_date"].unique().tolist())
    combinations = [
        {
            "category": row["category"],
            "product_id": row["product_id"],
            "hub_id": int(row["hub_id"]),
        }
        for row in df[["category", "product_id", "hub_id"]]
        .drop_duplicates()
        .to_dict(orient="records")
    ]

    return {
        "hubs": hubs,
        "products": products,
        "categories": categories,
        "dates": dates,
        "combinations": combinations,
    }


def _resolve_patch(
    body: SimulateRequest,
    base_state,
) -> tuple[ScenarioPatch, str]:
    query = (body.scenario_query or "").strip()

    if body.patch is not None:
        return body.patch, query

    if not query:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "needs_clarification",
                "clarification_questions": [
                    "Please describe a what-if scenario before running the simulation."
                ],
            },
        )

    understanding = understand_scenario(query, base_state)
    if understanding.status == "needs_clarification":
        raise HTTPException(
            status_code=422,
            detail={
                "status": "needs_clarification",
                "clarification_questions": understanding.clarification_questions,
            },
        )

    if understanding.patch is None:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "needs_clarification",
                "clarification_questions": [
                    "Could not resolve scenario parameters. Please provide more detail."
                ],
            },
        )

    return understanding.patch, query


@router.get("/context")
def get_planning_context(current_user: PlanningUser):
    del current_user
    try:
        return _load_context_data()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load planning context: {exc}",
        ) from exc


@router.post("/understand")
def understand_planning_scenario(
    body: UnderstandScenarioRequest,
    current_user: PlanningUser,
):
    del current_user
    try:
        base_state = build_base_state(
            hub_id=body.hub_id,
            product_id=body.product_id,
            category=body.category,
            simulation_date=body.simulation_date,
        )
        result = understand_scenario(body.scenario_query.strip(), base_state)
        return _to_jsonable(result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Scenario understanding failed: {exc}",
        ) from exc


@router.post("/simulate")
def simulate_planning(
    body: SimulateRequest,
    current_user: PlanningUser,
):
    del current_user
    try:
        base_state = build_base_state(
            hub_id=body.hub_id,
            product_id=body.product_id,
            category=body.category,
            simulation_date=body.simulation_date,
        )

        patch, scenario_query = _resolve_patch(body, base_state)

        config = PlanningPipelineConfig(
            base_state=base_state,
            patch=patch,
            planning_window_days=body.planning_window_days,
            n_worlds=body.n_worlds,
            random_seed=body.random_seed,
            skip_llm=body.skip_llm,
            auto_select_all_decisions=body.auto_select_all_decisions,
        )

        result = run_full_planning_pipeline(
            config,
            selected_decision_ids=body.selected_decision_ids,
        )

        payload = _to_jsonable(result)
        payload["scenario_query"] = scenario_query or body.scenario_query or ""
        payload["applied_patch"] = _to_jsonable(patch)
        return payload

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Simulation pipeline failed: {exc}",
        ) from exc
