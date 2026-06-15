from __future__ import annotations

import statistics

from simulation_models import OutcomeSummary, SimulationResult
from state_models import ScenarioState


def discover_outcomes(
    scenario: ScenarioState,
    simulation_results: list[SimulationResult],
) -> OutcomeSummary:
    if not simulation_results:
        raise ValueError("simulation_results must not be empty")

    total_worlds = len(simulation_results)
    stockout_worlds = sum(
        1 for result in simulation_results if result.stockout_occurred
    )
    stockout_probability = stockout_worlds / total_worlds

    avg_ending_inventory = statistics.mean(
        result.ending_inventory for result in simulation_results
    )
    avg_shortage_quantity = statistics.mean(
        result.shortage_quantity for result in simulation_results
    )
    avg_days_below_safety_stock = statistics.mean(
        result.days_below_safety_stock for result in simulation_results
    )

    best_case_world = min(
        simulation_results,
        key=lambda result: (result.shortage_quantity, -result.ending_inventory),
    )
    worst_case_world = max(
        simulation_results,
        key=lambda result: (result.shortage_quantity, -result.ending_inventory),
    )
    most_likely_world = min(
        simulation_results,
        key=lambda result: (
            abs(result.ending_inventory - avg_ending_inventory)
            + abs(result.shortage_quantity - avg_shortage_quantity),
            result.world_id,
        ),
    )

    signals: list[str] = []
    if stockout_probability > 0.5:
        signals.append("high_stockout_risk")
    if avg_ending_inventory > 2 * scenario.inventory.safety_stock:
        signals.append("excess_inventory")
    if avg_days_below_safety_stock > 0:
        signals.append("late_replenishment_risk")

    return OutcomeSummary(
        stockout_probability=stockout_probability,
        avg_ending_inventory=avg_ending_inventory,
        avg_shortage_quantity=avg_shortage_quantity,
        avg_days_below_safety_stock=avg_days_below_safety_stock,
        best_case_world=best_case_world,
        most_likely_world=most_likely_world,
        worst_case_world=worst_case_world,
        signals=signals,
    )
