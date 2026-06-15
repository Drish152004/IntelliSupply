from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from base_state import DEFAULT_FORECAST_HORIZON
from demand_reforecaster import patch_affects_forecast_drivers, reforecast_demand
from scenario_models import ScenarioPatch
from scenario_understanding_agent import ScenarioValidator

from state_models import (
    DemandState,
    EventState,
    ForecastState,
    InventoryState,
    ReplenishmentState,
    RiskState,
    ScenarioState,
    SimulationState,
)

def _copy_base_sections(
    base_state: SimulationState,
) -> tuple[
    InventoryState,
    DemandState,
    ForecastState,
    EventState,
    ReplenishmentState,
    RiskState,
]:
    return (
        deepcopy(base_state.inventory),
        deepcopy(base_state.demand),
        deepcopy(base_state.forecast),
        deepcopy(base_state.event),
        deepcopy(base_state.replenishment),
        deepcopy(base_state.risk),
    )

def _apply_inventory_patch(
    inventory: InventoryState,
    patch: ScenarioPatch,
) -> InventoryState:
    if not patch.inventory:
        return inventory
    if patch.inventory.current_stock_delta is not None:
        inventory = replace(
            inventory,
            current_stock=(
                inventory.current_stock
                + patch.inventory.current_stock_delta
            ),
        )

    if patch.inventory.safety_stock_multiplier is not None:
        inventory = replace(
            inventory,
            safety_stock=(
                inventory.safety_stock
                * patch.inventory.safety_stock_multiplier
            ),
        )
    return inventory

def _slice_forecast(
    forecast: ForecastState,
    base_forecast_daily: list[float],
    horizon: int,
) -> ForecastState:
    return replace(forecast, forecast_daily=base_forecast_daily[:horizon])

def _scale_forecast(
    forecast: ForecastState,
    multiplier: float,
) -> ForecastState:
    if multiplier == 1.0:
        return forecast

    scaled_daily = [value * multiplier for value in forecast.forecast_daily]
    scaled_lower = forecast.lower_bound * multiplier
    scaled_upper = forecast.upper_bound * multiplier
    return replace(
        forecast,
        forecast_daily=scaled_daily,
        predicted_demand=forecast.predicted_demand * multiplier,
        lower_bound=scaled_lower,
        upper_bound=scaled_upper,
        forecast_uncertainty=scaled_upper - scaled_lower,
    )

def _demand_multiplier(patch: ScenarioPatch) -> float:
    if patch.demand and patch.demand.demand_multiplier is not None:
        return patch.demand.demand_multiplier
    return 1.0

def _apply_event_patch(
    event: EventState,
    patch: ScenarioPatch,
) -> EventState:
    if not patch.event:
        return event

    if patch.event.promotion is not None:
        event = replace(
            event,
            promotion=int(patch.event.promotion),
        )

    if patch.event.epidemic is not None:
        event = replace(
            event,
            epidemic=int(patch.event.epidemic),
        )

    if patch.event.seasonality is not None:
        event = replace(
            event,
            seasonality=patch.event.seasonality.lower(),
        )
    return event

def _apply_replenishment_patch(
    replenishment: ReplenishmentState,
    patch: ScenarioPatch,
) -> ReplenishmentState:
    if not patch.replenishment:
        return replenishment
    if (
        patch.replenishment.lead_time_days_delta is not None
        and replenishment.lead_time_days is not None
    ):
        replenishment = replace(
            replenishment,
            lead_time_days=(
                replenishment.lead_time_days
                + patch.replenishment.lead_time_days_delta
            ),
        )
    if (
        patch.replenishment.actual_delay_days_delta is not None
        and replenishment.actual_delay_days is not None
    ):
        replenishment = replace(
            replenishment,
            actual_delay_days=(
                replenishment.actual_delay_days
                + patch.replenishment.actual_delay_days_delta
            ),
        )
    return replenishment

def build_scenario_state(
    base_state: SimulationState,
    patch: ScenarioPatch,
    planning_window_days: int | None = None,
) -> ScenarioState:
    """
    Apply a validated ScenarioPatch to a SimulationState.
    Stage 2A: copy-and-patch for inventory, replenishment, and event fields.
    Stage 2B: reforecast demand when promotion/seasonality/epidemic change;
    scale forecast when demand_multiplier is set (after reforecast if both apply).
    """
    ScenarioValidator.validate_against_state(patch, base_state)
    horizon = patch.planning_window_days or planning_window_days
    if horizon is None or horizon <= 0:
        raise ValueError(
            "planning_window_days is required. "
            "Set it on the patch or pass it to build_scenario_state."
        )
    needs_reforecast = patch_affects_forecast_drivers(patch)
    if needs_reforecast:
        if horizon > DEFAULT_FORECAST_HORIZON:
            raise ValueError(
                f"Planning window {horizon} exceeds model forecast "
                f"horizon ({DEFAULT_FORECAST_HORIZON} days)."
            )
    else:
        available_days = len(base_state.forecast.forecast_daily)
        if horizon > available_days:
            raise ValueError(
                f"Planning window {horizon} exceeds available forecast "
                f"horizon ({available_days} days)."
            )
    inventory, demand, forecast, event, replenishment, risk = (
        _copy_base_sections(base_state)
    )
    inventory = _apply_inventory_patch(inventory, patch)
    event = _apply_event_patch(event, patch)
    if needs_reforecast:
        forecast = reforecast_demand(
            base_state,
            event,
            forecast,
            horizon,
        )
    else:
        forecast = _slice_forecast(
            forecast,
            base_state.forecast.forecast_daily,
            horizon,
        )
    multiplier = _demand_multiplier(patch)
    if multiplier != 1.0:
        forecast = _scale_forecast(forecast, multiplier)
    replenishment = _apply_replenishment_patch(replenishment, patch)
    return ScenarioState(
        hub_id=base_state.hub_id,
        product_id=base_state.product_id,
        category=base_state.category,
        simulation_date=base_state.simulation_date,
        inventory=inventory,
        demand=demand,
        forecast=forecast,
        event=event,
        replenishment=replenishment,
        risk=risk,
        planning_window_days=horizon,
        applied_patch=patch,
    )