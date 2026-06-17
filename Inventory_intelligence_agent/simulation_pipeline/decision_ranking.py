from __future__ import annotations

from recommendation_models import DecisionComparison, RankedDecision

_WEIGHTS = {
    "stockout": 0.40,
    "shortage": 0.30,
    "days_ss": 0.20,
    "ending_inv": 0.10,
}

_SHORTAGE_CAP = 500.0
_DAYS_BELOW_SAFETY_STOCK_CAP = 7.0
_ENDING_INVENTORY_CAP = 500.0


def _benefit_values(comparison: DecisionComparison) -> dict[str, float]:
    return {
        "stockout": -comparison.stockout_probability_change,
        "shortage": comparison.shortage_reduction,
        "days_ss": -comparison.days_below_safety_stock_change,
        "ending_inv": comparison.ending_inventory_change,
    }


def absolute_utility_score(comparison: DecisionComparison) -> float:
    """Absolute intervention effectiveness on a 0–100 scale (not peer-normalized)."""
    benefits = _benefit_values(comparison)
    stockout_benefit = max(0.0, benefits["stockout"])
    shortage_benefit = min(1.0, max(0.0, benefits["shortage"] / _SHORTAGE_CAP))
    days_benefit = min(
        1.0,
        max(0.0, benefits["days_ss"] / _DAYS_BELOW_SAFETY_STOCK_CAP),
    )
    ending_benefit = min(1.0, max(0.0, benefits["ending_inv"] / _ENDING_INVENTORY_CAP))
    weighted = sum(_WEIGHTS[key] * value for key, value in {
        "stockout": stockout_benefit,
        "shortage": shortage_benefit,
        "days_ss": days_benefit,
        "ending_inv": ending_benefit,
    }.items())
    return round(min(100.0, max(0.0, weighted * 100.0)), 1)


def rank_decisions(comparisons: list[DecisionComparison]) -> list[RankedDecision]:
    if not comparisons:
        return []

    scored = [
        (
            absolute_utility_score(comparison),
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
            utility_score=utility,
        )
        for rank, (utility, _decision_id, comparison) in enumerate(scored, start=1)
    ]
