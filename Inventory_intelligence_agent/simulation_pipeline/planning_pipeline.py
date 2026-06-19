from __future__ import annotations

import sys
from pathlib import Path

_AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))
import env_setup  # noqa: F401 — loads repo root .env

from base_state import build_base_state
from baseline_des import simulate_worlds
from decision_comparison import compare_decisions
from decision_generation import generate_decisions
from action_executors import execute_decision_if_auto_approved
from automation_policy_store import append_action_audit_log, ensure_automation_csv_files
from decision_models import ActionExecutionResult, Decision, ExecutionDecision
from decision_ranking import rank_decisions
from decision_selection import (
    build_decision_selection_request,
    resolve_selected_decisions,
)
from decision_simulation import simulate_decisions
from decision_simulation_models import DecisionSimulationResult
from explainability_payload import build_explainability_payload
from llm_explanation import generate_llm_explanation
from monte_carlo_world_generator import generate_simulated_worlds
from outcome_discovery import discover_outcomes
from recommendation_engine import build_recommendation_summary
from recommendation_models import (
    BaselinePlanningResult,
    PlanningPipelineConfig,
    PlanningPipelineResult,
)
from policy_evaluator import evaluate_policy
from scenario_models import ScenarioPatch
from scenario_state_builder import build_scenario_state
from simulation_models import OutcomeSummary
from state_models import ScenarioState, SimulationState

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _resolve_data_dir(config: PlanningPipelineConfig) -> Path:
    return config.data_dir or DEFAULT_DATA_DIR


def run_baseline_planning(config: PlanningPipelineConfig) -> BaselinePlanningResult:
    scenario = build_scenario_state(
        config.base_state,
        config.patch,
        planning_window_days=config.planning_window_days,
    )
    data_dir = _resolve_data_dir(config)
    worlds = generate_simulated_worlds(
        scenario,
        n_worlds=config.n_worlds,
        random_seed=config.random_seed,
        data_dir=data_dir,
    )
    simulation_results = simulate_worlds(scenario, worlds)
    outcomes = discover_outcomes(scenario, simulation_results)
    decisions = generate_decisions(
        scenario,
        outcomes,
        data_dir=data_dir,
        peer_hub_states=config.peer_hub_states,
    )
    selection_request = build_decision_selection_request(
        scenario,
        outcomes,
        decisions,
    )
    return BaselinePlanningResult(
        scenario=scenario,
        outcomes=outcomes,
        decisions=decisions,
        selection_request=selection_request,
    )


def run_decision_evaluation_and_recommendation(
    baseline: BaselinePlanningResult,
    selected_decision_ids: list[str],
    config: PlanningPipelineConfig,
) -> PlanningPipelineResult:
    ensure_automation_csv_files()
    selected = resolve_selected_decisions(baseline.decisions, selected_decision_ids)
    data_dir = _resolve_data_dir(config)
    decision_results = simulate_decisions(
        baseline.scenario,
        selected,
        n_worlds=config.n_worlds,
        random_seed=config.random_seed,
        data_dir=data_dir,
    )
    comparisons = compare_decisions(baseline.outcomes, decision_results)
    ranked = rank_decisions(comparisons)
    recommendation = build_recommendation_summary(
        baseline.outcomes,
        ranked,
        decision_results,
    )
    policy_evaluations: list[ExecutionDecision] = []
    execution_results: list[ActionExecutionResult] = []

    recommended = recommendation.recommended_decision
    if recommended is not None:
        execution_decision = evaluate_policy(
            recommended.decision,
            utility_score=recommended.utility_score,
        )
        policy_evaluations.append(execution_decision)
        execution_result = execute_decision_if_auto_approved(
            execution_decision,
            baseline.scenario,
        )
        execution_results.append(execution_result)

        after_state = execution_result.execution_details.get("after_state")
        if execution_decision.status == "AUTO_APPROVED":
            after_state = execution_result.execution_details

        append_action_audit_log(
            decision_id=recommended.decision.decision_id,
            decision_type=recommended.decision.decision_type.value,
            decision_parameters=recommended.decision.parameters,
            policy_type=execution_decision.policy_type,
            execution_status=execution_decision.status,
            reason=execution_decision.reason,
            before_state=execution_result.execution_details.get("before_state"),
            after_state=after_state,
        )

    payload = build_explainability_payload(
        baseline.scenario,
        baseline.outcomes,
        recommendation,
        ranked,
        decision_results,
    )
    explanation = generate_llm_explanation(payload, skip_llm=config.skip_llm)
    return PlanningPipelineResult(
        scenario=baseline.scenario,
        outcomes=baseline.outcomes,
        decisions=baseline.decisions,
        decision_results=decision_results,
        comparison_results=comparisons,
        ranked_decisions=ranked,
        recommendation_summary=recommendation,
        policy_evaluations=policy_evaluations,
        execution_results=execution_results,
        explainability_payload=payload,
        llm_explanation=explanation,
    )


def run_full_planning_pipeline(
    config: PlanningPipelineConfig,
    *,
    selected_decision_ids: list[str] | None = None,
) -> PlanningPipelineResult:
    baseline = run_baseline_planning(config)
    if selected_decision_ids is None:
        if config.auto_select_all_decisions:
            selected_decision_ids = [d.decision_id for d in baseline.decisions]
        else:
            raise ValueError(
                "selected_decision_ids required (or set auto_select_all_decisions=True)"
            )
    return run_decision_evaluation_and_recommendation(
        baseline,
        selected_decision_ids,
        config,
    )


def simulate_selected_decisions(
    *,
    baseline_scenario: ScenarioState,
    selected_decisions: list[Decision],
    planning_window_days: int | None = None,
    n_worlds: int = 1000,
    random_seed: int | None = None,
    data_dir: Path | None = None,
    peer_hub_states: list[SimulationState] | None = None,
) -> list[DecisionSimulationResult]:
    """Stage-7-only wrapper for callers that do not need stages 8–12."""
    _ = planning_window_days, peer_hub_states
    return simulate_decisions(
        baseline_scenario,
        selected_decisions,
        n_worlds=n_worlds,
        random_seed=random_seed,
        data_dir=data_dir or DEFAULT_DATA_DIR,
    )


def run_baseline_simulation(
    *,
    hub_id: str,
    product_id: str,
    category: str,
    simulation_date: str,
    patch: ScenarioPatch,
    planning_window_days: int | None = None,
    n_worlds: int = 1000,
    random_seed: int | None = None,
    data_dir: Path | None = None,
    peer_hub_states: list[SimulationState] | None = None,
) -> tuple[OutcomeSummary, list[Decision]]:
    """Backward-compatible helper returning (outcomes, decisions)."""
    base_state = build_base_state(
        hub_id=hub_id,
        product_id=product_id,
        category=category,
        simulation_date=simulation_date,
    )
    config = PlanningPipelineConfig(
        base_state=base_state,
        patch=patch,
        planning_window_days=planning_window_days,
        n_worlds=n_worlds,
        random_seed=random_seed,
        data_dir=data_dir,
        peer_hub_states=peer_hub_states,
    )
    result = run_baseline_planning(config)
    return result.outcomes, result.decisions
