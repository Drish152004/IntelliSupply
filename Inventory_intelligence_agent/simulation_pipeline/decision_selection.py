from __future__ import annotations

from decision_models import Decision
from recommendation_models import DecisionSelectionRequest
from simulation_models import OutcomeSummary
from state_models import ScenarioState


def _baseline_metrics(outcome: OutcomeSummary) -> dict:
    return {
        "stockout_probability": outcome.stockout_probability,
        "avg_ending_inventory": outcome.avg_ending_inventory,
        "avg_shortage_quantity": outcome.avg_shortage_quantity,
        "avg_days_below_safety_stock": outcome.avg_days_below_safety_stock,
        "signals": list(outcome.signals),
    }


def _decision_summary(decision: Decision) -> dict:
    return {
        "decision_id": decision.decision_id,
        "title": decision.title,
        "decision_type": decision.decision_type.value,
        "rationale": decision.rationale,
        "parameters": dict(decision.parameters),
    }


def build_decision_selection_request(
    scenario: ScenarioState,
    baseline_outcome: OutcomeSummary,
    decisions: list[Decision],
) -> DecisionSelectionRequest:
    baseline_summary = {
        "hub_id": scenario.hub_id,
        "product_id": scenario.product_id,
        "category": scenario.category,
        **_baseline_metrics(baseline_outcome),
    }
    return DecisionSelectionRequest(
        baseline_summary=baseline_summary,
        candidate_decisions=[_decision_summary(d) for d in decisions],
    )


def resolve_selected_decisions(
    decisions: list[Decision],
    selected_decision_ids: list[str],
) -> list[Decision]:
    if not selected_decision_ids:
        return []

    by_id = {d.decision_id: d for d in decisions}
    unknown = [did for did in selected_decision_ids if did not in by_id]
    if unknown:
        raise ValueError(f"Unknown decision_id(s): {unknown}")

    return [by_id[did] for did in selected_decision_ids]
