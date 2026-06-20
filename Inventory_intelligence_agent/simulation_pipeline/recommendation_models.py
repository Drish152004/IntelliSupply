from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from decision_models import ActionExecutionResult, Decision, ExecutionDecision
from decision_simulation_models import DecisionSimulationResult
from scenario_models import ScenarioPatch
from simulation_models import OutcomeSummary
from state_models import ScenarioState, SimulationState


@dataclass
class DecisionComparison:
    decision: Decision
    stockout_probability_change: float
    shortage_reduction: float
    ending_inventory_change: float
    days_below_safety_stock_change: float


@dataclass
class RankedDecision:
    rank: int
    decision: Decision
    comparison: DecisionComparison
    impact_score: float


@dataclass
class RecommendationSummary:
    recommended_decision: RankedDecision | None
    explanation: str


@dataclass
class LLMExplanation:
    analyst_report: str


@dataclass
class DecisionSelectionRequest:
    baseline_summary: dict[str, Any]
    candidate_decisions: list[dict[str, Any]]


@dataclass
class PlanningPipelineConfig:
    base_state: SimulationState
    patch: ScenarioPatch
    planning_window_days: int | None = None
    n_worlds: int = 1000
    random_seed: int | None = None
    data_dir: Path | None = None
    peer_hub_states: list[SimulationState] | None = None
    skip_llm: bool = False
    auto_select_all_decisions: bool = False


@dataclass
class BaselinePlanningResult:
    scenario: ScenarioState
    outcomes: OutcomeSummary
    decisions: list[Decision]
    selection_request: DecisionSelectionRequest


@dataclass
class PlanningPipelineResult:
    scenario: ScenarioState
    outcomes: OutcomeSummary
    decisions: list[Decision]
    decision_results: list[DecisionSimulationResult]
    comparison_results: list[DecisionComparison]
    ranked_decisions: list[RankedDecision]
    recommendation_summary: RecommendationSummary
    policy_evaluations: list[ExecutionDecision]
    execution_results: list[ActionExecutionResult]
    llm_explanation: LLMExplanation
