from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from scenario_models import ScenarioPatch


@dataclass
class InventoryState:
    current_stock: int

    safety_stock: float

    threshold_quantity: float
    threshold_gap: float
    threshold_status: str

    coverage_days: float
    days_of_inventory_remaining: float

    velocity_score: float
    velocity_label: str

    inventory_status: str


@dataclass
class DemandState:
    rolling_7_avg_demand: float
    rolling_30_avg_demand: float

    demand_growth_pct: float

    previous_year_demand: Optional[float]
    yoy_demand_change_pct: Optional[float]
    yoy_trend_label: str

    demand_cv: float
    volatility_label: str


@dataclass
class ForecastState:
    forecast_date: str

    predicted_demand: float

    lower_bound: float
    upper_bound: float

    forecast_uncertainty: float

    confidence_score: float

    forecast_daily: list[float]


@dataclass
class RiskState:
    stock_coverage_risk: float
    demand_volatility_risk: float
    seasonality_risk: float
    replenishment_delay_risk: float

    composite_risk_score: float

    risk_level: str

    primary_risk_driver: str


@dataclass
class EventState:
    promotion: int

    seasonality: str

    epidemic: int


@dataclass
class ReplenishmentState:
    has_incoming_replenishment: bool

    quantity_ordered: Optional[int]
    quantity_received: Optional[int]

    lead_time_days: Optional[int]
    actual_delay_days: Optional[int]

    replenishment_status: Optional[str]

    priority: Optional[str]

    expected_arrival_date: Optional[str]
    actual_arrival_date: Optional[str]


@dataclass
class SimulationState:
    hub_id: str

    product_id: str

    category: str

    simulation_date: str

    inventory: InventoryState

    demand: DemandState

    forecast: ForecastState

    risk: RiskState

    event: EventState

    replenishment: ReplenishmentState


@dataclass
class ScenarioState:
    hub_id: str

    product_id: str

    category: str

    simulation_date: str

    inventory: InventoryState

    demand: DemandState

    forecast: ForecastState

    event: EventState

    replenishment: ReplenishmentState

    risk: RiskState

    planning_window_days: int

    applied_patch: ScenarioPatch
