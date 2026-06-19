from __future__ import annotations

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
    run_full_planning_pipeline,
)
from recommendation_models import PlanningPipelineConfig
from scenario_models import ScenarioPatch
from simulation_models import OutcomeSummary


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return obj.dict()
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return {
                k: _serialize(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        except Exception:
            pass
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def pretty_print(label: str, value: Any) -> None:
    print(f"\n===== {label} =====")
    if isinstance(value, (list, tuple)):
        print(f"Count: {len(value)}\n")
        for i, item in enumerate(value, start=1):
            try:
                dumped = json.dumps(item, default=_serialize, indent=2)
            except TypeError:
                dumped = json.dumps(_serialize(item), indent=2)
            print(f"[{i}] {dumped}\n")
    else:
        try:
            print(json.dumps(value, default=_serialize, indent=2))
        except TypeError:
            print(_serialize(value))


def _outcome_metrics(outcome: OutcomeSummary) -> dict[str, float | list[str]]:
    return {
        "stockout_probability": outcome.stockout_probability,
        "avg_ending_inventory": outcome.avg_ending_inventory,
        "avg_shortage_quantity": outcome.avg_shortage_quantity,
        "avg_days_below_safety_stock": outcome.avg_days_below_safety_stock,
        "signals": outcome.signals,
    }


def print_comparison(
    baseline: OutcomeSummary,
    results: list[DecisionSimulationResult],
) -> None:
    print("\n===== Baseline vs Decision Outcomes =====")
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


def main() -> None:
    patch = ScenarioPatch(
        demand={"demand_multiplier": 1.25},
    )

    base_state = build_base_state(
        hub_id="0",
        product_id="P0001",
        category="Electronics",
        simulation_date="2024-01-31",
    )
    config = PlanningPipelineConfig(
        base_state=base_state,
        patch=patch,
        planning_window_days=7,
        n_worlds=100,
        random_seed=42,
        auto_select_all_decisions=True,
        skip_llm=True,
    )

    pipeline_result = run_full_planning_pipeline(config)

    pretty_print("Baseline Outcomes", pipeline_result.outcomes)
    pretty_print("Selected Decisions", pipeline_result.decisions)
    pretty_print("Decision Simulation Results", pipeline_result.decision_results)
    pretty_print("Ranked Decisions", pipeline_result.ranked_decisions)
    pretty_print("Recommendation", pipeline_result.recommendation_summary)
    pretty_print("LLM Explanation", pipeline_result.llm_explanation)
    print_comparison(pipeline_result.outcomes, pipeline_result.decision_results)


if __name__ == "__main__":
    main()
