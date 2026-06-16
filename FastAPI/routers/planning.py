"""Inventory planning and simulation API routes."""

from __future__ import annotations

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from dependencies.auth import TokenUser, require_roles

# Imported from Inventory_intelligence_agent/simulation_pipeline thanks to bootstrap path additions
from scenario_models import ScenarioPatch
from recommendation_models import PlanningPipelineConfig
from base_state import build_base_state
from planning_pipeline import run_full_planning_pipeline

router = APIRouter(prefix="/planning", tags=["planning"])

PlanningUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "inventory_manager", "logistics_manager")),
]


class RunPlanningRequest(BaseModel):
    hub_id: str
    product_id: str
    category: str
    simulation_date: str
    patch: Optional[ScenarioPatch] = None
    planning_window_days: Optional[int] = None
    n_worlds: int = 100
    random_seed: Optional[int] = 42
    skip_llm: bool = True
    selected_decision_ids: Optional[List[str]] = None
    auto_select_all_decisions: bool = True


@router.get("/fixtures")
def get_planning_fixtures(current_user: PlanningUser):
    del current_user
    try:
        import pandas as pd
        from base_state import DATA_DIR

        # Load unique options from forecast CSV to ensure combinations exist
        df = pd.read_csv(
            DATA_DIR / "demand_forecast_daily.csv",
            usecols=["hub_id", "product_id", "category", "forecast_date"],
        )

        # Get unique values
        hubs = sorted(df["hub_id"].unique().tolist())
        products = sorted(df["product_id"].unique().tolist())
        categories = sorted(df["category"].unique().tolist())
        dates = sorted(df["forecast_date"].unique().tolist())

        # Extract the list of valid combinations to filter dynamically on frontend
        combinations = (
            df[["category", "product_id", "hub_id"]]
            .drop_duplicates()
            .to_dict(orient="records")
        )

        return {
            "hubs": hubs,
            "products": products,
            "categories": categories,
            "dates": dates,
            "combinations": combinations,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load fixtures: {exc}") from exc


@router.post("/run")
def run_planning_simulation(
    body: RunPlanningRequest,
    current_user: PlanningUser,
):
    del current_user
    try:
        # 1. Load the base state from daily CSV snapshots matching the filters
        base_state = build_base_state(
            hub_id=body.hub_id,
            product_id=body.product_id,
            category=body.category,
            simulation_date=body.simulation_date,
        )

        # 2. Build simulation run config
        config = PlanningPipelineConfig(
            base_state=base_state,
            patch=body.patch or ScenarioPatch(),
            planning_window_days=body.planning_window_days,
            n_worlds=body.n_worlds,
            random_seed=body.random_seed,
            skip_llm=body.skip_llm,
            auto_select_all_decisions=body.auto_select_all_decisions,
        )

        # 3. Execute Stages 0-12 of the planning and decision intelligence pipeline
        result = run_full_planning_pipeline(
            config,
            selected_decision_ids=body.selected_decision_ids,
        )

        # 4. Serialize the dataclasses, lists, and enums safely to JSON
        return jsonable_encoder(result)

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation pipeline failed: {exc}") from exc
