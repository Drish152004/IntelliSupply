from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from decision_models import Decision
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
    score: float


@dataclass
class RecommendationSummary:
    recommended_decision: RankedDecision | None
    explanation: str


@dataclass
class ExplainabilityPayload:
    scenario_summary: dict[str, Any]
    baseline_summary: dict[str, Any]
    recommendation_summary: dict[str, Any]
    ranked_decisions_summary: list[dict[str, Any]]
    best_case_summary: dict[str, Any]
    most_likely_summary: dict[str, Any]
    worst_case_summary: dict[str, Any]


@dataclass
class LLMExplanation:
    executive_summary: str
    recommended_action: str
    baseline_analysis: str
    decision_comparison: str
    best_case_analysis: str
    most_likely_analysis: str
    worst_case_analysis: str


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
    explainability_payload: ExplainabilityPayload
    llm_explanation: LLMExplanation
