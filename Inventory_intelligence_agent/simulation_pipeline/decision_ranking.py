from __future__ import annotations

from recommendation_models import DecisionComparison, RankedDecision
from simulation_models import OutcomeSummary

_WEIGHTS = {
    "stockout": 0.40,
    "shortage": 0.30,
    "days_ss": 0.20,
    "ending_inv": 0.10,
}


def _benefit_values(comparison: DecisionComparison) -> dict[str, float]:
    return {
        "stockout": -comparison.stockout_probability_change,
        "shortage": comparison.shortage_reduction,
        "days_ss": -comparison.days_below_safety_stock_change,
        "ending_inv": comparison.ending_inventory_change,
    }


def _relative_improvement(baseline: float, benefit: float) -> float:
    if baseline == 0:
        return 1.0 if benefit > 0 else 0.0
    return max(0.0, benefit / abs(baseline))


def absolute_impact_score(
    comparison: DecisionComparison,
    baseline: OutcomeSummary,
) -> float:
    """Relative intervention effectiveness vs baseline on a 0–100 scale."""
    benefits = _benefit_values(comparison)
    baseline_values = {
        "stockout": baseline.stockout_probability,
        "shortage": baseline.avg_shortage_quantity,
        "days_ss": baseline.avg_days_below_safety_stock,
        "ending_inv": baseline.avg_ending_inventory,
    }
    weighted = sum(
        _WEIGHTS[key] * _relative_improvement(baseline_values[key], benefits[key])
        for key in _WEIGHTS
    )
    return round(min(100.0, max(0.0, weighted * 100.0)), 1)


def rank_decisions(
    comparisons: list[DecisionComparison],
    baseline: OutcomeSummary,
) -> list[RankedDecision]:
    if not comparisons:
        return []

    scored = [
        (
            absolute_impact_score(comparison, baseline),
            comparison.decision.decision_id,
            comparison,
        )
        for comparison in comparisons
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))

    return [
        RankedDecision(
            rank=rank,
            decision=comparison.decision,
            comparison=comparison,
            impact_score=impact,
        )
        for rank, (impact, _decision_id, comparison) in enumerate(scored, start=1)
    ]
