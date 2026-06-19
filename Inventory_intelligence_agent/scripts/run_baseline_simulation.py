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
from planning_pipeline import run_baseline_planning
from recommendation_models import PlanningPipelineConfig
from scenario_models import ScenarioPatch


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
    )
    result = run_baseline_planning(config)

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

    pretty_print("Outcomes", result.outcomes)
    pretty_print("Decisions", result.decisions)
    pretty_print("Selection Request", result.selection_request)


if __name__ == "__main__":
    main()
