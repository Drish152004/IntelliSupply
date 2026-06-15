from __future__ import annotations

from pathlib import Path

from baseline_des import simulate_worlds
from decision_application import apply_decision
from decision_models import Decision
from decision_simulation_models import DecisionSimulationResult
from monte_carlo_world_generator import generate_simulated_worlds
from outcome_discovery import discover_outcomes
from state_models import ScenarioState


def simulate_decisions(
    baseline_scenario: ScenarioState,
    selected_decisions: list[Decision],
    *,
    n_worlds: int = 1000,
    random_seed: int | None = None,
    data_dir: Path | None = None,
) -> list[DecisionSimulationResult]:
    """
    Simulate each selected decision independently against the same baseline scenario.

    For each decision: apply, generate Monte Carlo worlds, run DES, discover outcomes.
    The same random_seed is used for every decision so world sampling is comparable.
    """
    if not selected_decisions:
        return []

    results: list[DecisionSimulationResult] = []
    for decision in selected_decisions:
        modified = apply_decision(baseline_scenario, decision)
        worlds = generate_simulated_worlds(
            modified,
            n_worlds=n_worlds,
            random_seed=random_seed,
            data_dir=data_dir,
        )
        simulation_results = simulate_worlds(modified, worlds)
        outcome = discover_outcomes(modified, simulation_results)
        results.append(
            DecisionSimulationResult(
                decision=decision,
                scenario=modified,
                outcome=outcome,
            )
        )
    return results
