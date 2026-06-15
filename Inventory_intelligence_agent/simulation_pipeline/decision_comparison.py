from __future__ import annotations

from decision_simulation_models import DecisionSimulationResult
from recommendation_models import DecisionComparison
from simulation_models import OutcomeSummary


def compare_decisions(
    baseline_outcome: OutcomeSummary,
    decision_results: list[DecisionSimulationResult],
) -> list[DecisionComparison]:
    comparisons: list[DecisionComparison] = []
    for result in decision_results:
        outcome = result.outcome
        comparisons.append(
            DecisionComparison(
                decision=result.decision,
                stockout_probability_change=(
                    outcome.stockout_probability - baseline_outcome.stockout_probability
                ),
                shortage_reduction=(
                    baseline_outcome.avg_shortage_quantity - outcome.avg_shortage_quantity
                ),
                ending_inventory_change=(
                    outcome.avg_ending_inventory - baseline_outcome.avg_ending_inventory
                ),
                days_below_safety_stock_change=(
                    outcome.avg_days_below_safety_stock
                    - baseline_outcome.avg_days_below_safety_stock
                ),
            )
        )
    return comparisons
