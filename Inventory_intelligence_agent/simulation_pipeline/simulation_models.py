from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationDay:
    day: int
    starting_inventory: float
    demand: float
    replenishment_received: float
    ending_inventory: float
    below_safety_stock: bool
    stockout_occurred: bool


@dataclass
class SimulationResult:
    world_id: int

    ending_inventory: float
    minimum_inventory: float

    stockout_occurred: bool
    stockout_day: Optional[int]

    shortage_quantity: float

    safety_stock_breached: bool
    days_below_safety_stock: int

    daily_log: list[SimulationDay]


@dataclass
class OutcomeSummary:
    stockout_probability: float

    avg_ending_inventory: float
    avg_shortage_quantity: float
    avg_days_below_safety_stock: float

    best_case_world: SimulationResult
    most_likely_world: SimulationResult
    worst_case_world: SimulationResult

    signals: list[str]
