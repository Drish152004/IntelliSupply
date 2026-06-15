from pathlib import Path

import pandas as pd

from state_models import (
    InventoryState,
    DemandState,
    ForecastState,
    RiskState,
    EventState,
    ReplenishmentState,
    SimulationState,
)

DATA_DIR = Path(__file__).parent.parent / "data"

DEFAULT_FORECAST_HORIZON = 30

inventory_health_df = pd.read_csv(
    DATA_DIR / "inventory_health_daily.csv"
)
demand_analysis_df = pd.read_csv(
    DATA_DIR / "demand_analysis_daily.csv"
)
forecast_df = pd.read_csv(
    DATA_DIR / "demand_forecast_daily.csv"
)
risk_df = pd.read_csv(
    DATA_DIR / "inventory_risk_daily.csv"
)
replenishment_df = pd.read_csv(
    DATA_DIR / "replenishment_orders.csv"
)

def _latest_row(
    df: pd.DataFrame,
    date_col: str,
    simulation_date: str,
):
    eligible = df[df[date_col] <= simulation_date]

    if eligible.empty:
        raise ValueError(
            f"No rows found before {simulation_date}"
        )

    return eligible.sort_values(
        date_col,
        ascending=False
    ).iloc[0]


def _hub_filter_value(hub_id: str):
    if inventory_health_df["hub_id"].dtype.kind in "iu":
        try:
            return int(hub_id)
        except ValueError:
            pass
    return hub_id


def _load_forecast_daily(
    hub_key,
    product_id: str,
    category: str,
    simulation_date: str,
    max_horizon: int = DEFAULT_FORECAST_HORIZON,
) -> list[float]:
    product_rows = forecast_df[
        (forecast_df["hub_id"] == hub_key)
        & (forecast_df["product_id"] == product_id)
        & (forecast_df["category"] == category)
    ]
    if product_rows.empty:
        raise ValueError("No forecast found for product")

    horizon_one = product_rows[
        product_rows["forecast_horizon_day"] == 1
    ]
    horizon_one = horizon_one[
        horizon_one["forecast_date"] <= simulation_date
    ]
    if horizon_one.empty:
        raise ValueError("No forecast found for product")

    anchor = horizon_one.sort_values(
        "forecast_date",
        ascending=False,
    ).iloc[0]

    batch = product_rows[
        product_rows["generated_at"] == anchor["generated_at"]
    ].sort_values("forecast_horizon_day")

    batch = batch[batch["forecast_horizon_day"] <= max_horizon]
    if len(batch) < max_horizon:
        raise ValueError(
            f"Expected {max_horizon} forecast days, found {len(batch)}."
        )

    return batch["predicted_demand"].astype(float).tolist()


def build_base_state(
    hub_id: str,
    product_id: str,
    category: str,
    simulation_date: str,
) -> SimulationState:

    hub_key = _hub_filter_value(hub_id)

    inventory_rows = inventory_health_df[
        (inventory_health_df["hub_id"] == hub_key)
        & (inventory_health_df["product_id"] == product_id)
        & (inventory_health_df["category"] == category)
    ]
    inventory_row = _latest_row(
        inventory_rows,
        "health_date",
        simulation_date,
    )

    demand_rows = demand_analysis_df[
        (demand_analysis_df["hub_id"] == hub_key)
        & (demand_analysis_df["product_id"] == product_id)
        & (demand_analysis_df["category"] == category)
    ]
    demand_row = _latest_row(
        demand_rows,
        "demand_date",
        simulation_date,
    )

    risk_rows = risk_df[
        (risk_df["hub_id"] == hub_key)
        & (risk_df["product_id"] == product_id)
        & (risk_df["category"] == category)
    ]
    risk_row = _latest_row(
        risk_rows,
        "risk_date",
        simulation_date,
    )

    forecast_rows = forecast_df[
        (forecast_df["hub_id"] == hub_key)
        & (forecast_df["product_id"] == product_id)
        & (forecast_df["category"] == category)
        & (forecast_df["forecast_horizon_day"] == 1)
    ]
    if forecast_rows.empty:
        raise ValueError(
            "No forecast found for product"
        )
    forecast_row = _latest_row(
        forecast_rows,
        "forecast_date",
        simulation_date,
    )
    replenishment_rows = replenishment_df[
        (replenishment_df["hub_id"] == hub_key)
        & (replenishment_df["product_id"] == product_id)
        & (replenishment_df["category"] == category)
    ]

    future_orders = replenishment_rows[
        replenishment_rows["actual_arrival_date"]
        >= simulation_date
    ]

    inventory = InventoryState(
        current_stock=int(
            inventory_row["current_stock"]
        ),
        safety_stock=float(
            inventory_row["safety_stock"]
        ),
        threshold_quantity=float(
            inventory_row["threshold_quantity"]
        ),
        threshold_gap=float(
            inventory_row["threshold_gap"]
        ),
        threshold_status=str(
            inventory_row["threshold_status"]
        ),
        coverage_days=float(
            inventory_row["coverage_days"]
        ),
        days_of_inventory_remaining=float(
            inventory_row[
                "days_of_inventory_remaining"
            ]
        ),
        velocity_score=float(
            inventory_row["velocity_score"]
        ),
        velocity_label=str(
            inventory_row["velocity_label"]
        ),
        inventory_status=str(
            inventory_row["inventory_status"]
        ),
    )

    demand = DemandState(
        rolling_7_avg_demand=float(
            demand_row["rolling_7_avg_demand"]
        ),
        rolling_30_avg_demand=float(
            demand_row["rolling_30_avg_demand"]
        ),
        demand_growth_pct=float(
            demand_row["demand_growth_pct"]
        ),
        previous_year_demand=demand_row[
            "previous_year_demand"
        ],
        yoy_demand_change_pct=demand_row[
            "yoy_demand_change_pct"
        ],
        yoy_trend_label=str(
            demand_row["yoy_trend_label"]
        ),
        demand_cv=float(
            demand_row["demand_cv"]
        ),
        volatility_label=str(
            demand_row["volatility_label"]
        ),
    )

    lower_bound = float(
        forecast_row["lower_bound"]
    )

    upper_bound = float(
        forecast_row["upper_bound"]
    )

    forecast = ForecastState(
        forecast_date=str(
            forecast_row["forecast_date"]
        ),
        predicted_demand=float(
            forecast_row["predicted_demand"]
        ),
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        forecast_uncertainty=(
            upper_bound - lower_bound
        ),
        confidence_score=float(
            forecast_row["confidence_score"]
        ),
        forecast_daily=_load_forecast_daily(
            hub_key,
            product_id,
            category,
            simulation_date,
        ),
    )

    risk = RiskState(
        stock_coverage_risk=float(
            risk_row["stock_coverage_risk"]
        ),
        demand_volatility_risk=float(
            risk_row["demand_volatility_risk"]
        ),
        seasonality_risk=float(
            risk_row["seasonality_risk"]
        ),
        replenishment_delay_risk=float(
            risk_row[
                "replenishment_delay_risk"
            ]
        ),
        composite_risk_score=float(
            risk_row[
                "composite_risk_score"
            ]
        ),
        risk_level=str(
            risk_row["risk_level"]
        ),
        primary_risk_driver=str(
            risk_row[
                "primary_risk_driver"
            ]
        ),
    )

    event = EventState(
        promotion=int(
            risk_row["promotion"]
        ),
        seasonality=str(
            risk_row["seasonality"]
        ),
        epidemic=int(
            risk_row["epidemic"]
        ),
    )

    if future_orders.empty:
        replenishment = ReplenishmentState(
            has_incoming_replenishment=False,
            quantity_ordered=None,
            quantity_received=None,
            lead_time_days=None,
            actual_delay_days=None,
            replenishment_status=None,
            priority=None,
            expected_arrival_date=None,
            actual_arrival_date=None,
        )

    else:

        order = future_orders.sort_values(
            "actual_arrival_date"
        ).iloc[0]
        replenishment = ReplenishmentState(
            has_incoming_replenishment=True,
            quantity_ordered=int(
                order["quantity_ordered"]
            ),
            quantity_received=int(
                order["quantity_received"]
            ),
            lead_time_days=int(
                order["lead_time_days"]
            ),
            actual_delay_days=int(
                order["actual_delay_days"]
            ),
            replenishment_status=str(
                order[
                    "replenishment_status"
                ]
            ),
            priority=str(
                order["priority"]
            ),
            expected_arrival_date=str(
                order[
                    "expected_arrival_date"
                ]
            ),
            actual_arrival_date=str(
                order[
                    "actual_arrival_date"
                ]
            ),
        )

    return SimulationState(
        hub_id=str(hub_key),

        product_id=product_id,

        category=category,

        simulation_date=simulation_date,

        inventory=inventory,

        demand=demand,

        forecast=forecast,

        risk=risk,

        event=event,

        replenishment=replenishment,
    )