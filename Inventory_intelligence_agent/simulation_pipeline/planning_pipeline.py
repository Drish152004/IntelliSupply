from __future__ import annotations

import sys
from pathlib import Path

_AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))
import env_setup  # noqa: F401 — loads repo root .env

from baseline_des import simulate_worlds
from decision_comparison import compare_decisions
from decision_generation import generate_decisions
from action_executors import execute_decision_if_auto_approved
from automation_policy_store import append_action_audit_log, ensure_automation_csv_files
from decision_models import ActionExecutionResult, ExecutionDecision
from decision_ranking import rank_decisions
from decision_selection import (
    build_decision_selection_request,
    resolve_selected_decisions,
)
from decision_simulation import simulate_decisions
from explainability_payload import build_analyst_brief
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
from scenario_state_builder import build_scenario_state

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
    ranked = rank_decisions(comparisons, baseline.outcomes)
    recommendation = build_recommendation_summary(
        baseline.outcomes,
        ranked,
        decision_results,
    )
    policy_evaluations: list[ExecutionDecision] = []
    execution_results: list[ActionExecutionResult] = []

    for result in decision_results:
        policy_evaluations.append(evaluate_policy(result.decision))

    recommended = recommendation.recommended_decision
    if recommended is not None:
        execution_decision = next(
            evaluation
            for evaluation in policy_evaluations
            if evaluation.decision.decision_id == recommended.decision.decision_id
        )
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

    brief = build_analyst_brief(
        baseline.scenario,
        baseline.outcomes,
        recommendation,
        ranked,
        decision_results,
    )
    explanation = generate_llm_explanation(brief, skip_llm=config.skip_llm)
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
