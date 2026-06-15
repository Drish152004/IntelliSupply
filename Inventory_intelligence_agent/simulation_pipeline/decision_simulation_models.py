from __future__ import annotations

from dataclasses import dataclass

from decision_models import Decision
from simulation_models import OutcomeSummary
from state_models import ScenarioState


@dataclass
class DecisionScenario:
    decision: Decision
    scenario: ScenarioState


@dataclass
class DecisionSimulationResult:
    decision: Decision
    scenario: ScenarioState
    outcome: OutcomeSummary
