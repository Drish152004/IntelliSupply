from __future__ import annotations

from recommendation_models import DecisionComparison, RankedDecision

_WEIGHTS = {
    "stockout": 0.40,
    "shortage": 0.30,
    "days_ss": 0.20,
    "ending_inv": 0.10,
}


def _min_max_normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [1.0]
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _benefit_values(comparison: DecisionComparison) -> dict[str, float]:
    return {
        "stockout": -comparison.stockout_probability_change,
        "shortage": comparison.shortage_reduction,
        "days_ss": -comparison.days_below_safety_stock_change,
        "ending_inv": comparison.ending_inventory_change,
    }


def _score_comparison(
    comparison: DecisionComparison,
    normalized: dict[str, list[float]],
    index: int,
) -> float:
    benefits = _benefit_values(comparison)
    return sum(
        _WEIGHTS[key] * normalized[key][index]
        for key in _WEIGHTS
    )


def rank_decisions(comparisons: list[DecisionComparison]) -> list[RankedDecision]:
    if not comparisons:
        return []

    benefit_keys = list(_WEIGHTS.keys())
    raw_by_key: dict[str, list[float]] = {key: [] for key in benefit_keys}
    for comparison in comparisons:
        benefits = _benefit_values(comparison)
        for key in benefit_keys:
            raw_by_key[key].append(benefits[key])

    normalized = {key: _min_max_normalize(raw_by_key[key]) for key in benefit_keys}

    scored = [
        (
            _score_comparison(comparison, normalized, index),
            comparison.decision.decision_id,
            comparison,
        )
        for index, comparison in enumerate(comparisons)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))

    return [
        RankedDecision(
            rank=rank,
            decision=comparison.decision,
            comparison=comparison,
            score=score,
        )
        for rank, (score, _decision_id, comparison) in enumerate(scored, start=1)
    ]
