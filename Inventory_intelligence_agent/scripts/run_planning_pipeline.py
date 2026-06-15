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
from planning_pipeline import (
    run_baseline_planning,
    run_decision_evaluation_and_recommendation,
)
from recommendation_models import PlanningPipelineConfig
from scenario_models import ScenarioPatch


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
    return obj


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run full planning pipeline with human decision selection.",
    )
    parser.add_argument("--hub-id", default="0")
    parser.add_argument("--product-id", default="P0001")
    parser.add_argument("--category", default="Electronics")
    parser.add_argument("--simulation-date", default="2024-01-31")
    parser.add_argument("--n-worlds", type=int, default=100)
    parser.add_argument("--random-seed", type=int, default=42)
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
    args = parser.parse_args()

    patch = ScenarioPatch(
        planning_window_days=7,
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
        n_worlds=args.n_worlds,
        random_seed=args.random_seed,
        skip_llm=args.skip_llm,
    )

    _print_section("Phase 1 — Baseline planning")
    baseline = run_baseline_planning(config)
    print(json.dumps(_serialize(baseline.selection_request), indent=2))

    if args.auto_select_all:
        selected_ids = [d.decision_id for d in baseline.decisions]
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

    explanation = result.llm_explanation
    _print_section("Executive Summary")
    print(explanation.executive_summary)
    _print_section("Recommended Action")
    print(explanation.recommended_action)
    _print_section("Baseline Analysis")
    print(explanation.baseline_analysis)
    _print_section("Decision Comparison")
    print(explanation.decision_comparison)
    _print_section("Best Case")
    print(explanation.best_case_analysis)
    _print_section("Most Likely Case")
    print(explanation.most_likely_analysis)
    _print_section("Worst Case")
    print(explanation.worst_case_analysis)


if __name__ == "__main__":
    main()
