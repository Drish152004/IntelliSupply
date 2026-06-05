"""CLI entry point for the full demand forecasting pipeline demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml_services.demand_forecasting.full_pipeline.config import (  # noqa: E402
    DAILY_MODEL_PATH,
    DEFAULT_DAILY_HORIZON,
    DEFAULT_DATASET_KIND,
    DEFAULT_WEEKLY_HORIZON,
    LADE_DIR,
    OUTPUT_DIR,
    WEEKLY_STRATEGY_PATH,
)
from ml_services.demand_forecasting.full_pipeline.pipeline import (  # noqa: E402
    DemandForecastPipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LaDe demand forecasting pipeline")
    parser.add_argument(
        "--granularity",
        choices=["daily", "weekly"],
        default="daily",
        help="Forecast grain (default: daily)",
    )
    parser.add_argument("--horizon", type=int, default=None, help="Days or weeks ahead")
    parser.add_argument("--city", type=str, default=None, help="Filter to one city")
    parser.add_argument(
        "--dataset-kind",
        default=DEFAULT_DATASET_KIND,
        help="LaDe folder: delivery or pickup",
    )
    parser.add_argument(
        "--weekly-strategy",
        default=None,
        help="Override weekly strategy (daily_sum, hierarchical, native)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip writing CSV/JSON outputs",
    )
    args = parser.parse_args()

    if not LADE_DIR.exists():
        raise FileNotFoundError(
            f"LaDe data not found at {LADE_DIR}. "
            "Place delivery CSVs under LaDe/delivery/ or set LADE_DATA_DIR."
        )
    if not DAILY_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Daily model not found at {DAILY_MODEL_PATH}. "
            "Train the model or copy artifacts into ml_services/demand_forecasting/models/."
        )

    horizon = args.horizon
    if horizon is None:
        horizon = DEFAULT_DAILY_HORIZON if args.granularity == "daily" else DEFAULT_WEEKLY_HORIZON

    print(f"Pipeline: LaDe {args.dataset_kind} -> panel -> {args.granularity} forecast")
    print(f"Horizon : {horizon} {'days' if args.granularity == 'daily' else 'weeks'}")
    if args.city:
        print(f"City    : {args.city}")

    pipeline = DemandForecastPipeline(
        model_path=DAILY_MODEL_PATH,
        lade_dir=LADE_DIR,
        output_dir=OUTPUT_DIR,
        strategy_path=WEEKLY_STRATEGY_PATH,
    )
    result = pipeline.run(
        granularity=args.granularity,
        horizon=horizon,
        city=args.city,
        dataset_kind=args.dataset_kind,
        weekly_strategy=args.weekly_strategy,
        save_outputs=not args.no_save,
    )

    print(f"\nPanel rows processed : {result.panel_rows:,}")
    print(f"Regions forecast     : {result.summary.n_regions}")
    print(f"Period               : {result.summary.period_start} -> {result.summary.period_end}")
    print(f"Total predicted      : {result.summary.total_predicted:,.0f}")
    print(f"Strategy             : {result.strategy}")

    if result.output_dir:
        print(f"Outputs written to   : {result.output_dir}")

    print("\nTop cities:")
    for row in result.by_city[:5]:
        print(f"  {row['city']}: {row['predicted_demand']:,}")


if __name__ == "__main__":
    main()
