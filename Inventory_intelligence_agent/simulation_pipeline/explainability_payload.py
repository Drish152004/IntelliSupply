from __future__ import annotations

from decision_simulation_models import DecisionSimulationResult
from recommendation_models import RankedDecision, RecommendationSummary
from simulation_models import OutcomeSummary, SimulationDay, SimulationResult
from state_models import ScenarioState


def _aggregate_metrics(outcome: OutcomeSummary) -> dict:
    return {
        "stockout_probability": outcome.stockout_probability,
        "avg_ending_inventory": outcome.avg_ending_inventory,
        "avg_shortage_quantity": outcome.avg_shortage_quantity,
        "avg_days_below_safety_stock": outcome.avg_days_below_safety_stock,
        "signals": list(outcome.signals),
    }


def _comparison_dict(comparison) -> dict:
    return {
        "stockout_probability_change": comparison.stockout_probability_change,
        "shortage_reduction": comparison.shortage_reduction,
        "ending_inventory_change": comparison.ending_inventory_change,
        "days_below_safety_stock_change": comparison.days_below_safety_stock_change,
    }


def _day_event_score(day: SimulationDay, prev: SimulationDay | None) -> float:
    score = 0.0
    if day.stockout_occurred:
        score += 100.0
    if day.replenishment_received > 0:
        score += 50.0
    if prev is not None and day.below_safety_stock and not prev.below_safety_stock:
        score += 40.0
    elif day.below_safety_stock:
        score += 20.0
    score += min(day.demand, 100.0) * 0.1
    return score


def _event_type(day: SimulationDay, prev: SimulationDay | None) -> str:
    if day.stockout_occurred:
        return "stockout"
    if day.replenishment_received > 0:
        return "replenishment_received"
    if prev is not None and day.below_safety_stock and not prev.below_safety_stock:
        return "safety_stock_breach_start"
    if day.below_safety_stock:
        return "below_safety_stock"
    return "high_demand"


def extract_key_daily_events(
    daily_log: list[SimulationDay],
    *,
    max_events: int = 5,
) -> list[dict]:
    if not daily_log:
        return []

    scored: list[tuple[float, int, SimulationDay, SimulationDay | None]] = []
    for index, day in enumerate(daily_log):
        prev = daily_log[index - 1] if index > 0 else None
        scored.append((_day_event_score(day, prev), index, day, prev))

    scored.sort(key=lambda item: (-item[0], item[1]))
    events: list[dict] = []
    seen_days: set[int] = set()
    for _score, _index, day, prev in scored:
        if day.day in seen_days:
            continue
        seen_days.add(day.day)
        events.append(
            {
                "day": day.day,
                "event_type": _event_type(day, prev),
                "ending_inventory": day.ending_inventory,
                "demand": day.demand,
            }
        )
        if len(events) >= max_events:
            break
    return events


def _case_world_summary(world: SimulationResult, *, max_daily_events: int) -> dict:
    return {
        "world_id": world.world_id,
        "stockout_day": world.stockout_day,
        "ending_inventory": world.ending_inventory,
        "shortage_quantity": world.shortage_quantity,
        "key_daily_events": extract_key_daily_events(
            world.daily_log,
            max_events=max_daily_events,
        ),
    }


def _find_decision_outcome(
    decision_id: str,
    decision_results: list[DecisionSimulationResult],
) -> OutcomeSummary | None:
    for result in decision_results:
        if result.decision.decision_id == decision_id:
            return result.outcome
    return None


def build_analyst_brief(
    scenario: ScenarioState,
    baseline_outcome: OutcomeSummary,
    recommendation: RecommendationSummary,
    ranked_decisions: list[RankedDecision],
    decision_results: list[DecisionSimulationResult],
    *,
    top_n_decisions: int = 5,
    max_daily_events: int = 5,
) -> dict:
    situation = {
        "hub_id": scenario.hub_id,
        "product_id": scenario.product_id,
        "category": scenario.category,
        "simulation_date": scenario.simulation_date,
        "planning_window_days": scenario.planning_window_days,
        "current_stock": scenario.inventory.current_stock,
        "safety_stock": scenario.inventory.safety_stock,
        "coverage_days": scenario.inventory.coverage_days,
        "predicted_demand": scenario.forecast.predicted_demand,
        "risk_level": scenario.risk.risk_level,
        "composite_risk_score": scenario.risk.composite_risk_score,
    }

    baseline_risk = {
        **_aggregate_metrics(baseline_outcome),
        "outlook_if_no_action": {
            "best_case": _case_world_summary(
                baseline_outcome.best_case_world,
                max_daily_events=max_daily_events,
            ),
            "most_likely": _case_world_summary(
                baseline_outcome.most_likely_world,
                max_daily_events=max_daily_events,
            ),
            "worst_case": _case_world_summary(
                baseline_outcome.worst_case_world,
                max_daily_events=max_daily_events,
            ),
        },
    }

    if recommendation.recommended_decision is not None:
        rec = recommendation.recommended_decision
        recommendation_summary = {
            "selected_intervention": rec.decision.title,
            "decision_id": rec.decision.decision_id,
            "decision_type": rec.decision.decision_type.value,
            "impact_score": rec.impact_score,
            "expected_improvements": _comparison_dict(rec.comparison),
            "explanation": recommendation.explanation,
        }
        recommended_outcome = _find_decision_outcome(
            rec.decision.decision_id,
            decision_results,
        )
    else:
        recommendation_summary = {
            "selected_intervention": None,
            "impact_score": None,
            "expected_improvements": {},
            "explanation": recommendation.explanation,
        }
        recommended_outcome = None

    alternatives_considered = [
        {
            "rank": item.rank,
            "title": item.decision.title,
            "impact_score": item.impact_score,
            "expected_improvements": _comparison_dict(item.comparison),
        }
        for item in ranked_decisions[:top_n_decisions]
    ]

    if recommended_outcome is not None:
        outlook = {
            "best_case": _case_world_summary(
                recommended_outcome.best_case_world,
                max_daily_events=max_daily_events,
            ),
            "most_likely": _case_world_summary(
                recommended_outcome.most_likely_world,
                max_daily_events=max_daily_events,
            ),
            "worst_case": _case_world_summary(
                recommended_outcome.worst_case_world,
                max_daily_events=max_daily_events,
            ),
        }
    else:
        outlook = {
            "best_case": _case_world_summary(
                baseline_outcome.best_case_world,
                max_daily_events=max_daily_events,
            ),
            "most_likely": _case_world_summary(
                baseline_outcome.most_likely_world,
                max_daily_events=max_daily_events,
            ),
            "worst_case": _case_world_summary(
                baseline_outcome.worst_case_world,
                max_daily_events=max_daily_events,
            ),
        }

    return {
        "situation": situation,
        "baseline_risk": baseline_risk,
        "recommendation": recommendation_summary,
        "alternatives_considered": alternatives_considered,
        "outlook": outlook,
    }
