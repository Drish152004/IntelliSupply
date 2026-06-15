from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DEFAULT_DELAY_STATS_FILENAME = "replenishment_delay_stats.csv"
DEFAULT_FALLBACK_DELAY_STD = 1.0
MIN_SAMPLE_COUNT = 2


@dataclass(frozen=True)
class ReplenishmentDelayStats:
    delay_mean: float
    delay_std: float
    sample_count: int


def build_delay_stats_csv(
    data_dir: Path,
    output_path: Path | None = None,
) -> Path:
    data_dir = Path(data_dir)
    orders_path = data_dir / "replenishment_orders.csv"
    if not orders_path.exists():
        raise FileNotFoundError(f"Replenishment orders file not found: {orders_path}")

    output_path = output_path or data_dir / DEFAULT_DELAY_STATS_FILENAME
    orders = pd.read_csv(orders_path)

    grouped = (
        orders.groupby(["hub_id", "product_id", "category"], as_index=False)
        .agg(
            delay_mean=("actual_delay_days", "mean"),
            delay_std=("actual_delay_days", "std"),
            sample_count=("actual_delay_days", "count"),
        )
    )
    grouped["hub_id"] = grouped["hub_id"].astype(str)
    grouped["product_id"] = grouped["product_id"].astype(str)
    grouped["category"] = grouped["category"].astype(str)
    grouped["delay_std"] = grouped["delay_std"].fillna(0.0)
    grouped.to_csv(output_path, index=False)
    return output_path


def _stats_from_series(series: pd.Series) -> ReplenishmentDelayStats | None:
    values = series.dropna()
    if len(values) < MIN_SAMPLE_COUNT:
        return None
    std = float(values.std(ddof=1))
    if std <= 0.0:
        std = DEFAULT_FALLBACK_DELAY_STD
    return ReplenishmentDelayStats(
        delay_mean=float(values.mean()),
        delay_std=std,
        sample_count=int(len(values)),
    )


def _load_delay_stats_table(data_dir: Path) -> pd.DataFrame:
    stats_path = Path(data_dir) / DEFAULT_DELAY_STATS_FILENAME
    if not stats_path.exists():
        raise FileNotFoundError(
            f"Replenishment delay stats file not found: {stats_path}. "
            "Run replenishment_delay_stats.py to generate it."
        )
    stats = pd.read_csv(stats_path)
    stats["hub_id"] = stats["hub_id"].astype(str)
    stats["product_id"] = stats["product_id"].astype(str)
    stats["category"] = stats["category"].astype(str)
    return stats


def _load_orders(data_dir: Path) -> pd.DataFrame:
    orders_path = Path(data_dir) / "replenishment_orders.csv"
    orders = pd.read_csv(orders_path)
    orders["hub_id"] = orders["hub_id"].astype(str)
    return orders


def load_delay_stats(
    hub_id: str,
    product_id: str,
    category: str,
    data_dir: Path,
) -> ReplenishmentDelayStats:
    stats = _load_delay_stats_table(data_dir)
    hub_key = str(hub_id)
    product_key = str(product_id)
    category_key = str(category)

    exact = stats[
        (stats["hub_id"] == hub_key)
        & (stats["product_id"] == product_key)
        & (stats["category"] == category_key)
    ]
    if not exact.empty and int(exact.iloc[0]["sample_count"]) >= MIN_SAMPLE_COUNT:
        row = exact.iloc[0]
        delay_std = float(row["delay_std"])
        if delay_std <= 0.0:
            delay_std = DEFAULT_FALLBACK_DELAY_STD
        return ReplenishmentDelayStats(
            delay_mean=float(row["delay_mean"]),
            delay_std=delay_std,
            sample_count=int(row["sample_count"]),
        )

    orders = _load_orders(data_dir)

    hub_product_stats = _stats_from_series(
        orders[
            (orders["hub_id"] == hub_key)
            & (orders["product_id"] == product_key)
        ]["actual_delay_days"]
    )
    if hub_product_stats is not None:
        return hub_product_stats

    hub_category_stats = _stats_from_series(
        orders[
            (orders["hub_id"] == hub_key)
            & (orders["category"] == category_key)
        ]["actual_delay_days"]
    )
    if hub_category_stats is not None:
        return hub_category_stats

    global_stats = _stats_from_series(orders["actual_delay_days"])
    if global_stats is not None:
        return global_stats

    return ReplenishmentDelayStats(
        delay_mean=0.0,
        delay_std=DEFAULT_FALLBACK_DELAY_STD,
        sample_count=0,
    )


if __name__ == "__main__":
    project_data_dir = Path(__file__).resolve().parent.parent / "data"
    output = build_delay_stats_csv(project_data_dir)
    print(f"Wrote {output}")
