from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import env_setup  # noqa: F401 — loads repo root .env

_SIM_PIPELINE = ROOT / "simulation_pipeline"
if str(_SIM_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_SIM_PIPELINE))

from base_state import build_base_state
from decision_simulation_models import DecisionSimulationResult
from planning_pipeline import (
    run_baseline_planning,
    run_decision_evaluation_and_recommendation,
)
from recommendation_models import BaselinePlanningResult, PlanningPipelineConfig, PlanningPipelineResult
from scenario_models import ScenarioPatch
from simulation_models import OutcomeSummary


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "__dict__"):
        return {
            k: _serialize(v)
            for k, v in obj.__dict__.items()
            if not k.startswith("_")
        }
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _pretty_print(label: str, value: Any) -> None:
    _print_section(label)
    if isinstance(value, (list, tuple)):
        print(f"Count: {len(value)}\n")
        for index, item in enumerate(value, start=1):
            try:
                dumped = json.dumps(item, default=_serialize, indent=2)
            except TypeError:
                dumped = json.dumps(_serialize(item), indent=2)
            print(f"[{index}] {dumped}\n")
    else:
        try:
            print(json.dumps(value, default=_serialize, indent=2))
        except TypeError:
            print(json.dumps(_serialize(value), indent=2))


def _outcome_metrics(outcome: OutcomeSummary) -> dict[str, float | list[str]]:
    return {
        "stockout_probability": outcome.stockout_probability,
        "avg_ending_inventory": outcome.avg_ending_inventory,
        "avg_shortage_quantity": outcome.avg_shortage_quantity,
        "avg_days_below_safety_stock": outcome.avg_days_below_safety_stock,
        "signals": outcome.signals,
    }


def _print_comparison(
    baseline: OutcomeSummary,
    results: list[DecisionSimulationResult],
) -> None:
    _print_section("Baseline vs Decision Outcomes")
    baseline_metrics = _outcome_metrics(baseline)
    print(
        f"{'Decision':<40} "
        f"{'Stockout':>10} "
        f"{'Avg End Inv':>12} "
        f"{'Avg Shortage':>13} "
        f"{'Days < SS':>10}"
    )
    print("-" * 90)
    print(
        f"{'BASELINE':<40} "
        f"{baseline_metrics['stockout_probability']:>10.1%} "
        f"{baseline_metrics['avg_ending_inventory']:>12.1f} "
        f"{baseline_metrics['avg_shortage_quantity']:>13.1f} "
        f"{baseline_metrics['avg_days_below_safety_stock']:>10.1f}"
    )
    for result in results:
        metrics = _outcome_metrics(result.outcome)
        label = result.decision.title[:40]
        print(
            f"{label:<40} "
            f"{metrics['stockout_probability']:>10.1%} "
            f"{metrics['avg_ending_inventory']:>12.1f} "
            f"{metrics['avg_shortage_quantity']:>13.1f} "
            f"{metrics['avg_days_below_safety_stock']:>10.1f}"
        )


def _prompt_decision_ids(candidates: list[dict[str, Any]]) -> list[str]:
    print("\nCandidate interventions:")
    for item in candidates:
        print(f"  [{item['decision_id']}] {item['title']}")
        print(f"      {item['rationale']}")

    print(
        "\nEnter decision_id(s) to simulate (comma-separated), "
        "or 'all' for every option:"
    )
    raw = input("> ").strip()
    if raw.lower() == "all":
        return [item["decision_id"] for item in candidates]
    return [part.strip() for part in raw.split(",") if part.strip()]


def _print_baseline_outputs(baseline: BaselinePlanningResult, *, verbose: bool) -> None:
    print(json.dumps(_serialize(baseline.selection_request), indent=2))
    if verbose:
        _pretty_print("Outcomes", baseline.outcomes)
        _pretty_print("Decisions", baseline.decisions)


def _print_full_outputs(result: PlanningPipelineResult, *, verbose: bool) -> None:
    if verbose:
        _pretty_print("Baseline Outcomes", result.outcomes)
        _pretty_print("Selected Decisions", result.decisions)
        _pretty_print("Decision Simulation Results", result.decision_results)
        _pretty_print("Ranked Decisions", result.ranked_decisions)
        _pretty_print("Recommendation", result.recommendation_summary)
        _pretty_print("LLM Explanation", result.llm_explanation)
        _print_comparison(result.outcomes, result.decision_results)

    _print_section("Analysis Report")
    print(result.llm_explanation.analyst_report)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the planning pipeline CLI demo.",
    )
    parser.add_argument("--hub-id", default="0")
    parser.add_argument("--product-id", default="P0001")
    parser.add_argument("--category", default="Electronics")
    parser.add_argument("--simulation-date", default="2024-01-31")
    parser.add_argument("--n-worlds", type=int, default=100)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Run baseline planning only and exit before decision simulation.",
    )
    parser.add_argument(
        "--auto-select-all",
        action="store_true",
        help="Skip HITL and simulate all generated decisions.",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Use deterministic explanation templates instead of Groq.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed JSON dumps and baseline vs decision comparison table.",
    )
    args = parser.parse_args()

    patch = ScenarioPatch(
        demand={"demand_multiplier": 1.25},
    )
    base_state = build_base_state(
        hub_id=args.hub_id,
        product_id=args.product_id,
        category=args.category,
        simulation_date=args.simulation_date,
    )
    config = PlanningPipelineConfig(
        base_state=base_state,
        patch=patch,
        planning_window_days=7,
        n_worlds=args.n_worlds,
        random_seed=args.random_seed,
        skip_llm=args.skip_llm,
        auto_select_all_decisions=args.auto_select_all,
    )

    _print_section("Phase 1 — Baseline planning")
    baseline = run_baseline_planning(config)
    _print_baseline_outputs(baseline, verbose=args.verbose)

    if args.baseline_only:
        return

    if args.auto_select_all:
        selected_ids = [decision.decision_id for decision in baseline.decisions]
    else:
        selected_ids = _prompt_decision_ids(
            baseline.selection_request.candidate_decisions
        )

    _print_section("Phase 2 — Decision evaluation and recommendation")
    result = run_decision_evaluation_and_recommendation(
        baseline,
        selected_ids,
        config,
    )
    _print_full_outputs(result, verbose=args.verbose)


if __name__ == "__main__":
    main()
