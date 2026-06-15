from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from replenishment_delay_stats import load_delay_stats
from state_models import ScenarioState
from world_models import SimulatedWorld

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _effective_demand_cv(scenario: ScenarioState) -> float:
    demand_cv = scenario.demand.demand_cv
    forecast_uncertainty = scenario.forecast.forecast_uncertainty
    predicted_demand = scenario.forecast.predicted_demand
    forecast_error_cv = forecast_uncertainty / max(
        2.0 * predicted_demand,
        1e-9,
    )
    return math.sqrt(demand_cv**2 + forecast_error_cv**2)


def _sample_daily_demand(
    scenario: ScenarioState,
    rng: np.random.Generator,
    effective_cv: float,
) -> list[float]:
    horizon = scenario.planning_window_days
    forecast_daily = scenario.forecast.forecast_daily
    if len(forecast_daily) != horizon:
        raise ValueError(
            "forecast_daily length "
            f"({len(forecast_daily)}) must match planning_window_days ({horizon})"
        )

    daily_demand: list[float] = []
    for day in range(horizon):
        base = forecast_daily[day]
        std_dev = base * effective_cv
        sampled = float(rng.normal(base, std_dev))
        daily_demand.append(max(0.0, sampled))
    return daily_demand


def _sample_replenishment_arrival_day(
    scenario: ScenarioState,
    rng: np.random.Generator,
    delay_std: float,
) -> int | None:
    replenishment = scenario.replenishment
    if not replenishment.has_incoming_replenishment:
        return None
    if (
        replenishment.lead_time_days is None
        or replenishment.actual_delay_days is None
    ):
        return None

    jitter = float(rng.normal(loc=0.0, scale=delay_std))
    arrival_day = (
        replenishment.lead_time_days
        + replenishment.actual_delay_days
        + jitter
    )
    return int(round(arrival_day))


def generate_simulated_worlds(
    scenario: ScenarioState,
    n_worlds: int = 1000,
    random_seed: int | None = None,
    data_dir: Path | None = None,
) -> list[SimulatedWorld]:
    if n_worlds <= 0:
        raise ValueError("n_worlds must be positive")

    resolved_data_dir = data_dir or DEFAULT_DATA_DIR
    rng = np.random.default_rng(random_seed)
    effective_cv = _effective_demand_cv(scenario)
    delay_stats = load_delay_stats(
        scenario.hub_id,
        scenario.product_id,
        scenario.category,
        resolved_data_dir,
    )

    worlds: list[SimulatedWorld] = []
    for world_id in range(n_worlds):
        worlds.append(
            SimulatedWorld(
                world_id=world_id,
                daily_demand=_sample_daily_demand(
                    scenario,
                    rng,
                    effective_cv,
                ),
                replenishment_arrival_day=_sample_replenishment_arrival_day(
                    scenario,
                    rng,
                    delay_stats.delay_std,
                ),
            )
        )
    return worlds
