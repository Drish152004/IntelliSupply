from __future__ import annotations

from decision_simulation_models import DecisionSimulationResult
from recommendation_models import RankedDecision, RecommendationSummary
from simulation_models import OutcomeSummary


def _format_shortage_pct(baseline: OutcomeSummary, ranked: RankedDecision) -> str:
    base_qty = baseline.avg_shortage_quantity
    if base_qty <= 0:
        if ranked.comparison.shortage_reduction > 0:
            return "reduces projected shortage"
        return "does not worsen projected shortage"
    pct = (ranked.comparison.shortage_reduction / base_qty) * 100.0
    if pct > 0:
        return f"reduces average shortage by {pct:.0f}%"
    if pct < 0:
        return f"increases average shortage by {abs(pct):.0f}%"
    return "does not change average shortage"


def build_recommendation_summary(
    baseline_outcome: OutcomeSummary,
    ranked_decisions: list[RankedDecision],
    decision_results: list[DecisionSimulationResult],
) -> RecommendationSummary:
    _ = decision_results
    if not ranked_decisions:
        stockout_pct = baseline_outcome.stockout_probability * 100.0
        return RecommendationSummary(
            recommended_decision=None,
            explanation=(
                f"Current scenario has a {stockout_pct:.0f}% stockout probability. "
                "No interventions were evaluated; maintain current plan and monitor risk signals."
            ),
        )

    best = ranked_decisions[0]
    stockout_pct = baseline_outcome.stockout_probability * 100.0
    shortage_text = _format_shortage_pct(baseline_outcome, best)
    evaluated = len(ranked_decisions)
    explanation = (
        f"Current scenario has a {stockout_pct:.0f}% stockout probability. "
        f"{best.decision.title} {shortage_text} and is the highest scoring "
        f"intervention among {evaluated} evaluated option"
        f"{'' if evaluated == 1 else 's'}."
    )
    return RecommendationSummary(
        recommended_decision=best,
        explanation=explanation,
    )
