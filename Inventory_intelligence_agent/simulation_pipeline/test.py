"""

CLI to test the runtime pipeline (Stages 0–6).



Stage 0: build_base_state              -> SimulationState from offline CSVs

Stage 1: understand_scenario           -> ScenarioPatch or clarification questions

Stage 2: build_scenario_state          -> ScenarioState (copy-and-patch)

Stage 3: generate_simulated_worlds     -> List[SimulatedWorld] (Monte Carlo)

Stage 4: simulate_worlds               -> List[SimulationResult] (Baseline DES)

Stage 5: discover_outcomes             -> OutcomeSummary

Stage 6: generate_decisions            -> List[Decision]

Stage 7: apply_decision / simulate_decisions -> List[DecisionSimulationResult]

Stage 8: compare_decisions              -> List[DecisionComparison]

Stage 9: rank_decisions                 -> List[RankedDecision]

Stage 10: build_recommendation_summary  -> RecommendationSummary

Stage 11: build_explainability_payload  -> ExplainabilityPayload

Stage 12: generate_llm_explanation      -> LLMExplanation



Usage:

  python test.py

  python test.py --scenario "What if demand increases?"

  python test.py --base-state-only

  python test.py --stage2-only --patch-file patch.json --planning-window-days 7

  python test.py --deterministic-stage2

  python test.py --deterministic-stage3

  python test.py --deterministic-stage4

  python test.py --deterministic-stage5

  python test.py --deterministic-stage6

  python test.py --deterministic-stage7

  python test.py --deterministic-stages8-11

  python test.py --list-fixtures

"""



from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from dataclasses import replace
from pathlib import Path

_AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))
import env_setup  # noqa: F401 — loads repo root .env
from config.paths import ENV_FILE

import pandas as pd



from base_state import build_base_state

from baseline_des import simulate_world, simulate_worlds

from decision_application import apply_decision

from decision_generation import generate_decisions

from decision_models import Decision, DecisionType

from decision_simulation import simulate_decisions

from decision_simulation_models import DecisionSimulationResult

from decision_comparison import compare_decisions

from decision_ranking import rank_decisions

from decision_selection import (
    build_decision_selection_request,
    resolve_selected_decisions,
)

from explainability_payload import build_explainability_payload, extract_key_daily_events

from llm_explanation import generate_llm_explanation

from planning_pipeline import (
    run_baseline_planning,
    run_decision_evaluation_and_recommendation,
    run_full_planning_pipeline,
)

from recommendation_engine import build_recommendation_summary

from recommendation_models import PlanningPipelineConfig

from demand_reforecaster import reforecast_available

from monte_carlo_world_generator import generate_simulated_worlds

from outcome_discovery import discover_outcomes

from replenishment_delay_stats import load_delay_stats

from scenario_models import ScenarioPatch

from scenario_state_builder import build_scenario_state

from scenario_understanding_agent import understand_scenario

from simulation_models import OutcomeSummary, SimulationDay, SimulationResult

from state_models import ScenarioState, SimulationState

from world_models import SimulatedWorld



DATA_DIR = Path(__file__).parent.parent / "data"

DEFAULT_SCENARIO = "What if demand increases by 25% next week?"

DEFAULT_AMBIGUOUS_SCENARIO = "What if demand increases?"

DEFAULT_COMPOUND_SCENARIO = (

    "What if demand increases by 20% and inventory decreases by 200 units?"

)





def discover_default_fixture(

    prefer_replenishment: bool = True,

) -> dict[str, str]:

    simulation_date = "2024-01-31"



    health = pd.read_csv(

        DATA_DIR / "inventory_health_daily.csv",

        usecols=["hub_id", "product_id", "category", "health_date"],

    )

    demand = pd.read_csv(

        DATA_DIR / "demand_analysis_daily.csv",

        usecols=["hub_id", "product_id", "category", "demand_date"],

    )

    risk = pd.read_csv(

        DATA_DIR / "inventory_risk_daily.csv",

        usecols=["hub_id", "product_id", "category", "risk_date"],

    )

    forecast = pd.read_csv(

        DATA_DIR / "demand_forecast_daily.csv",

        usecols=[

            "hub_id",

            "product_id",

            "category",

            "forecast_date",

            "forecast_horizon_day",

        ],

    )

    replenishment = pd.read_csv(

        DATA_DIR / "replenishment_orders.csv",

        usecols=["hub_id", "product_id", "category", "actual_arrival_date"],

    )



    keys = ["hub_id", "product_id", "category"]

    common = (

        set(map(tuple, health[keys].drop_duplicates().values))

        & set(map(tuple, demand[keys].drop_duplicates().values))

        & set(map(tuple, risk[keys].drop_duplicates().values))

        & set(

            map(

                tuple,

                forecast[forecast["forecast_horizon_day"] == 1][keys]

                .drop_duplicates()

                .values,

            )

        )

    )



    future_orders = replenishment[

        replenishment["actual_arrival_date"] >= simulation_date

    ]

    future_keys = set(map(tuple, future_orders[keys].drop_duplicates().values))



    candidates = sorted(common & future_keys if prefer_replenishment else common)

    if prefer_replenishment and not candidates:

        candidates = sorted(common)



    for hub_id, product_id, category in candidates:

        try:

            build_base_state(

                hub_id=str(hub_id),

                product_id=product_id,

                category=category,

                simulation_date=simulation_date,

            )

            return {

                "hub_id": str(hub_id),

                "product_id": product_id,

                "category": category,

                "simulation_date": simulation_date,

            }

        except ValueError:

            continue



    raise RuntimeError(

        "Could not find a valid fixture in the bundled CSV data."

    )





def discover_fixture_without_replenishment() -> dict[str, str]:

    simulation_date = "2024-01-31"

    keys = ["hub_id", "product_id", "category"]

    health = pd.read_csv(

        DATA_DIR / "inventory_health_daily.csv",

        usecols=["hub_id", "product_id", "category", "health_date"],

    )

    demand = pd.read_csv(

        DATA_DIR / "demand_analysis_daily.csv",

        usecols=["hub_id", "product_id", "category", "demand_date"],

    )

    risk = pd.read_csv(

        DATA_DIR / "inventory_risk_daily.csv",

        usecols=["hub_id", "product_id", "category", "risk_date"],

    )

    forecast = pd.read_csv(

        DATA_DIR / "demand_forecast_daily.csv",

        usecols=[

            "hub_id",

            "product_id",

            "category",

            "forecast_date",

            "forecast_horizon_day",

        ],

    )

    replenishment = pd.read_csv(

        DATA_DIR / "replenishment_orders.csv",

        usecols=["hub_id", "product_id", "category", "actual_arrival_date"],

    )

    common = (

        set(map(tuple, health[keys].drop_duplicates().values))

        & set(map(tuple, demand[keys].drop_duplicates().values))

        & set(map(tuple, risk[keys].drop_duplicates().values))

        & set(

            map(

                tuple,

                forecast[forecast["forecast_horizon_day"] == 1][keys]

                .drop_duplicates()

                .values,

            )

        )

    )

    future_orders = replenishment[

        replenishment["actual_arrival_date"] >= simulation_date

    ]

    future_keys = set(map(tuple, future_orders[keys].drop_duplicates().values))

    candidates = sorted(common - future_keys)

    for hub_id, product_id, category in candidates:

        try:

            state = build_base_state(

                hub_id=str(hub_id),

                product_id=product_id,

                category=category,

                simulation_date=simulation_date,

            )

            if state.replenishment.has_incoming_replenishment:

                continue

            return {

                "hub_id": str(hub_id),

                "product_id": product_id,

                "category": category,

                "simulation_date": simulation_date,

            }

        except ValueError:

            continue

    raise RuntimeError(

        "Could not find a fixture without incoming replenishment."

    )





def list_fixtures(limit: int = 10) -> list[dict[str, str]]:

    fixture = discover_default_fixture()

    rows = [fixture]



    replenishment = pd.read_csv(

        DATA_DIR / "replenishment_orders.csv",

        usecols=["hub_id", "product_id", "category", "actual_arrival_date"],

    )

    future = replenishment[

        replenishment["actual_arrival_date"] >= fixture["simulation_date"]

    ]

    for _, row in future.drop_duplicates(

        subset=["hub_id", "product_id", "category"]

    ).head(limit - 1).iterrows():

        candidate = {

            "hub_id": str(row["hub_id"]),

            "product_id": row["product_id"],

            "category": row["category"],

            "simulation_date": fixture["simulation_date"],

        }

        try:

            build_base_state(**candidate)

            rows.append(candidate)

        except ValueError:

            continue

    return rows





def print_section(title: str) -> None:

    print()

    print("=" * len(title))

    print(title)

    print("=" * len(title))





def print_base_state_summary(state: SimulationState) -> None:

    print_section("Stage 0 - Base State")

    print(

        f"hub={state.hub_id}  product={state.product_id}  "

        f"category={state.category}  date={state.simulation_date}"

    )

    print(f"current_stock={state.inventory.current_stock}")

    print(f"safety_stock={state.inventory.safety_stock}")

    print(f"inventory_status={state.inventory.inventory_status}")

    print(f"rolling_7_avg_demand={state.demand.rolling_7_avg_demand:.2f}")

    print(f"predicted_demand={state.forecast.predicted_demand:.2f}")

    print(f"forecast_daily_len={len(state.forecast.forecast_daily)}")

    print(f"composite_risk_score={state.risk.composite_risk_score:.2f}")

    print(

        f"promotion={'on' if state.event.promotion else 'off'}  "

        f"seasonality={state.event.seasonality}  "

        f"epidemic={'on' if state.event.epidemic else 'off'}"

    )

    if state.replenishment.has_incoming_replenishment:

        print(

            "incoming_replenishment="

            f"qty={state.replenishment.quantity_ordered}, "

            f"lead_time_days={state.replenishment.lead_time_days}, "

            f"delay_days={state.replenishment.actual_delay_days}, "

            f"arrival={state.replenishment.actual_arrival_date}"

        )

    else:

        print("incoming_replenishment=none")





def print_scenario_result(result) -> None:

    print_section("Stage 1 - Scenario Understanding")

    print(f"status={result.status}")

    if result.status == "needs_clarification":

        print("clarification_questions:")

        for index, question in enumerate(result.clarification_questions, start=1):

            print(f"  {index}. {question}")

        return



    print("patch:")

    print(json.dumps(result.patch.model_dump(exclude_none=True), indent=2))





def print_scenario_state_summary(

    base_state: SimulationState,

    scenario_state: ScenarioState,

) -> None:

    print_section("Stage 2 - Scenario State")

    print(f"planning_window_days={scenario_state.planning_window_days}")

    print(

        f"current_stock: {base_state.inventory.current_stock} -> "

        f"{scenario_state.inventory.current_stock}"

    )

    print(

        f"safety_stock: {base_state.inventory.safety_stock:.2f} -> "

        f"{scenario_state.inventory.safety_stock:.2f}"

    )

    print(

        f"rolling_7_avg_demand: {base_state.demand.rolling_7_avg_demand:.2f} -> "

        f"{scenario_state.demand.rolling_7_avg_demand:.2f} "

        "(historical, unchanged)"

    )

    print(

        f"predicted_demand: {base_state.forecast.predicted_demand:.2f} -> "

        f"{scenario_state.forecast.predicted_demand:.2f}"

    )

    print(

        f"forecast_daily_len: {len(base_state.forecast.forecast_daily)} -> "

        f"{len(scenario_state.forecast.forecast_daily)}"

    )

    if scenario_state.forecast.forecast_daily:

        print(

            "forecast_daily_sample="

            f"{scenario_state.forecast.forecast_daily[:3]}"

        )

    print(

        f"promotion={'on' if scenario_state.event.promotion else 'off'}  "

        f"seasonality={scenario_state.event.seasonality}  "

        f"epidemic={'on' if scenario_state.event.epidemic else 'off'}"

    )

    if scenario_state.replenishment.has_incoming_replenishment:

        print(

            f"lead_time_days: {base_state.replenishment.lead_time_days} -> "

            f"{scenario_state.replenishment.lead_time_days}  "

            f"delay_days: {base_state.replenishment.actual_delay_days} -> "

            f"{scenario_state.replenishment.actual_delay_days}"

        )

    print(

        f"risk_unchanged="

        f"{scenario_state.risk.composite_risk_score == base_state.risk.composite_risk_score}"

    )





def print_stage4_summary(results: list[SimulationResult]) -> None:

    print_section("Stage 4 - Baseline DES")

    print(f"worlds_simulated={len(results)}")

    if not results:

        return



    stockout_count = sum(1 for result in results if result.stockout_occurred)

    safety_breach_count = sum(

        1 for result in results if result.safety_stock_breached

    )

    print(f"stockout_worlds={stockout_count}")

    print(f"safety_breach_worlds={safety_breach_count}")



    sample = results[0]

    print(

        f"sample_world_id={sample.world_id}  "

        f"ending_inventory={sample.ending_inventory:.2f}  "

        f"minimum_inventory={sample.minimum_inventory:.2f}  "

        f"stockout={sample.stockout_occurred}  "

        f"shortage_quantity={sample.shortage_quantity:.2f}"

    )

    print(f"daily_log_len={len(sample.daily_log)}")




def print_stage5_summary(outcome: OutcomeSummary) -> None:

    print_section("Stage 5 - Outcome Discovery")

    print(f"stockout_probability={outcome.stockout_probability:.4f}")

    print(f"avg_ending_inventory={outcome.avg_ending_inventory:.2f}")

    print(f"avg_shortage_quantity={outcome.avg_shortage_quantity:.2f}")

    print(f"avg_days_below_safety_stock={outcome.avg_days_below_safety_stock:.2f}")

    print(f"signals={outcome.signals}")



    for label, world in (

        ("best_case", outcome.best_case_world),

        ("most_likely", outcome.most_likely_world),

        ("worst_case", outcome.worst_case_world),

    ):

        print(

            f"{label}_world_id={world.world_id}  "

            f"ending_inventory={world.ending_inventory:.2f}  "

            f"shortage_quantity={world.shortage_quantity:.2f}  "

            f"stockout={world.stockout_occurred}  "

            f"daily_log_len={len(world.daily_log)}"

        )





def print_stage6_summary(decisions: list[Decision]) -> None:

    print_section("Stage 6 - Decision Generation")

    print(f"candidate_count={len(decisions)}")

    for decision in decisions:

        print(

            f"{decision.decision_id}  type={decision.decision_type.value}  "

            f"title={decision.title}"

        )

        print(f"  parameters={decision.parameters}")





def load_patch_file(path: Path) -> ScenarioPatch:

    data = json.loads(path.read_text(encoding="utf-8"))

    return ScenarioPatch.model_validate(data)





def run_deterministic_stage2_tests(fixture: dict[str, str]) -> int:

    print_section("Deterministic Stage 2 Tests")

    base = build_base_state(**fixture)

    failures = 0



    def check(name: str, condition: bool, detail: str = "") -> None:

        nonlocal failures

        if condition:

            print(f"  PASS  {name}")

        else:

            failures += 1

            suffix = f" — {detail}" if detail else ""

            print(f"  FAIL  {name}{suffix}")



    demand_patch = ScenarioPatch(

        planning_window_days=7,

        demand={"demand_multiplier": 1.25},

    )

    demand_state = build_scenario_state(base, demand_patch)

    check(

        "demand scales forecast_daily",

        demand_state.forecast.forecast_daily

        == [v * 1.25 for v in base.forecast.forecast_daily[:7]],

    )

    check(

        "demand leaves rolling avg unchanged",

        demand_state.demand.rolling_7_avg_demand

        == base.demand.rolling_7_avg_demand,

    )

    check(

        "demand leaves demand_cv unchanged",

        demand_state.demand.demand_cv == base.demand.demand_cv,

    )



    stock_delta = -min(50, max(0, base.inventory.current_stock - 1))

    inventory_patch = ScenarioPatch(

        planning_window_days=7,

        inventory={"current_stock_delta": stock_delta},

    )

    inventory_state = build_scenario_state(base, inventory_patch)

    check(

        "inventory delta applied",

        inventory_state.inventory.current_stock

        == base.inventory.current_stock + stock_delta,

    )

    check(

        "inventory leaves forecast unchanged",

        inventory_state.forecast.forecast_daily

        == base.forecast.forecast_daily[:7],

    )



    if reforecast_available():

        promotion_value = not bool(base.event.promotion)

        promotion_patch = ScenarioPatch(

            planning_window_days=7,

            event={"promotion": promotion_value},

        )

        promotion_state = build_scenario_state(base, promotion_patch)

        check(

            "promotion reforecast changes forecast_daily",

            promotion_state.forecast.forecast_daily

            != base.forecast.forecast_daily[:7],

        )

        check(

            "promotion event patched",

            promotion_state.event.promotion == int(promotion_value),

        )



        seasonality_patch = ScenarioPatch(

            planning_window_days=7,

            event={"seasonality": "summer"},

        )

        seasonality_state = build_scenario_state(base, seasonality_patch)

        check(

            "seasonality event patched",

            seasonality_state.event.seasonality == "summer",

        )

        check(

            "seasonality reforecast changes forecast_daily",

            seasonality_state.forecast.forecast_daily

            != base.forecast.forecast_daily[:7],

        )



        promo_mult_patch = ScenarioPatch(

            planning_window_days=7,

            event={"promotion": promotion_value},

            demand={"demand_multiplier": 1.20},

        )

        promo_mult_state = build_scenario_state(base, promo_mult_patch)

        expected_daily = [

            v * 1.20 for v in promotion_state.forecast.forecast_daily

        ]

        check(

            "promotion + demand_multiplier applies scale after reforecast",

            promo_mult_state.forecast.forecast_daily == expected_daily,

        )

    else:

        print(

            "  SKIP  Stage 2B reforecast tests "

            "(model artifact or joblib/xgboost unavailable)"

        )



    compound_patch = ScenarioPatch(

        planning_window_days=14,

        demand={"demand_multiplier": 1.20},

        inventory={"current_stock_delta": stock_delta},

        replenishment={"actual_delay_days_delta": 5},

    )

    compound_state = build_scenario_state(base, compound_patch)

    check(

        "compound demand + inventory",

        compound_state.forecast.forecast_daily[0]

        == base.forecast.forecast_daily[0] * 1.20

        and compound_state.inventory.current_stock

        == base.inventory.current_stock + stock_delta,

    )

    if base.replenishment.has_incoming_replenishment:

        check(

            "compound replenishment delay",

            compound_state.replenishment.actual_delay_days

            == base.replenishment.actual_delay_days + 5,

        )



    check(

        "risk copied unchanged",

        compound_state.risk == base.risk,

    )



    print()

    if failures:

        print(f"{failures} test(s) failed.")

        return 1

    print("All deterministic Stage 2 tests passed.")

    return 0





def _build_default_scenario_state(fixture: dict[str, str]) -> ScenarioState:

    base = build_base_state(**fixture)

    patch = ScenarioPatch(planning_window_days=7)

    return build_scenario_state(base, patch)





def _build_test_scenario(
    fixture: dict[str, str],
    *,
    current_stock: int,
    safety_stock: float,
    planning_window_days: int,
    has_incoming_replenishment: bool = False,
    quantity_ordered: int | None = None,
) -> ScenarioState:
    scenario = _build_default_scenario_state(fixture)
    inventory = replace(
        scenario.inventory,
        current_stock=current_stock,
        safety_stock=safety_stock,
    )
    replenishment = replace(
        scenario.replenishment,
        has_incoming_replenishment=has_incoming_replenishment,
        quantity_ordered=quantity_ordered,
    )
    return replace(
        scenario,
        planning_window_days=planning_window_days,
        inventory=inventory,
        replenishment=replenishment,
    )





def run_deterministic_stage3_tests() -> int:

    print_section("Deterministic Stage 3 Tests")

    failures = 0



    def check(name: str, condition: bool, detail: str = "") -> None:

        nonlocal failures

        if condition:

            print(f"  PASS  {name}")

        else:

            failures += 1

            suffix = f" — {detail}" if detail else ""

            print(f"  FAIL  {name}{suffix}")



    replenishment_fixture = discover_default_fixture(prefer_replenishment=True)

    replenishment_scenario = _build_default_scenario_state(replenishment_fixture)

    no_replenishment_fixture = discover_fixture_without_replenishment()

    no_replenishment_scenario = _build_default_scenario_state(

        no_replenishment_fixture

    )

    seed = 42

    n_worlds = 10

    worlds = generate_simulated_worlds(

        replenishment_scenario,

        n_worlds=n_worlds,

        random_seed=seed,

        data_dir=DATA_DIR,

    )

    worlds_repeat = generate_simulated_worlds(

        replenishment_scenario,

        n_worlds=n_worlds,

        random_seed=seed,

        data_dir=DATA_DIR,

    )



    check(

        "reproducibility",

        worlds == worlds_repeat,

    )

    check(

        "world count",

        len(worlds) == n_worlds,

    )

    check(

        "daily_demand length matches planning window",

        all(

            len(world.daily_demand)

            == replenishment_scenario.planning_window_days

            for world in worlds

        ),

    )

    check(

        "non-negative demand",

        all(value >= 0 for world in worlds for value in world.daily_demand),

    )

    world_signatures = {

        (

            tuple(world.daily_demand),

            world.replenishment_arrival_day,

        )

        for world in worlds

    }

    check(

        "worlds differ",

        len(world_signatures) >= 2,

    )



    large_worlds = generate_simulated_worlds(

        replenishment_scenario,

        n_worlds=5000,

        random_seed=seed,

        data_dir=DATA_DIR,

    )

    day_zero_mean = statistics.mean(

        world.daily_demand[0] for world in large_worlds

    )

    forecast_day_zero = replenishment_scenario.forecast.forecast_daily[0]

    tolerance = 0.15 * max(forecast_day_zero, 1.0)

    check(

        "sampled day-0 mean near forecast",

        abs(day_zero_mean - forecast_day_zero) <= tolerance,

        f"mean={day_zero_mean:.2f}, forecast={forecast_day_zero:.2f}",

    )



    no_replenishment_worlds = generate_simulated_worlds(

        no_replenishment_scenario,

        n_worlds=n_worlds,

        random_seed=seed,

        data_dir=DATA_DIR,

    )

    check(

        "no replenishment arrival day is None",

        all(

            world.replenishment_arrival_day is None

            for world in no_replenishment_worlds

        ),

    )



    check(

        "with replenishment arrival day is int",

        all(

            isinstance(world.replenishment_arrival_day, int)

            for world in large_worlds

        ),

    )

    delay_stats = load_delay_stats(

        replenishment_scenario.hub_id,

        replenishment_scenario.product_id,

        replenishment_scenario.category,

        DATA_DIR,

    )

    arrival_days = [

        world.replenishment_arrival_day

        for world in large_worlds

        if world.replenishment_arrival_day is not None

    ]

    arrival_std = statistics.pstdev(arrival_days)

    arrival_tolerance = max(0.35, 0.35 * delay_stats.delay_std)

    check(

        "arrival jitter std near delay_std",

        abs(arrival_std - delay_stats.delay_std) <= arrival_tolerance,

        f"sample_std={arrival_std:.2f}, delay_std={delay_stats.delay_std:.2f}",

    )



    print()

    if failures:

        print(f"{failures} test(s) failed.")

        return 1

    print("All deterministic Stage 3 tests passed.")

    return 0





def run_deterministic_stage4_tests() -> int:

    print_section("Deterministic Stage 4 Tests")

    failures = 0

    fixture = discover_default_fixture()



    def check(name: str, condition: bool, detail: str = "") -> None:

        nonlocal failures

        if condition:

            print(f"  PASS  {name}")

        else:

            failures += 1

            suffix = f" — {detail}" if detail else ""

            print(f"  FAIL  {name}{suffix}")



    depletion_scenario = _build_test_scenario(
        fixture,
        current_stock=100,
        safety_stock=50.0,
        planning_window_days=3,
    )

    depletion_world = SimulatedWorld(
        world_id=0,
        daily_demand=[10.0, 10.0, 10.0],
        replenishment_arrival_day=None,
    )

    depletion_result = simulate_world(depletion_scenario, depletion_world)

    check(
        "simple depletion ending inventory",
        depletion_result.ending_inventory == 70.0,
        f"got {depletion_result.ending_inventory}",
    )

    check(
        "simple depletion minimum inventory",
        depletion_result.minimum_inventory == 70.0,
        f"got {depletion_result.minimum_inventory}",
    )

    check(
        "simple depletion no stockout",
        not depletion_result.stockout_occurred,
    )

    check(
        "simple depletion daily log length",
        len(depletion_result.daily_log) == 3,
    )



    stockout_scenario = _build_test_scenario(
        fixture,
        current_stock=10,
        safety_stock=0.0,
        planning_window_days=3,
    )

    stockout_world = SimulatedWorld(
        world_id=1,
        daily_demand=[15.0, 15.0, 15.0],
        replenishment_arrival_day=None,
    )

    stockout_result = simulate_world(stockout_scenario, stockout_world)

    check(
        "stockout occurred",
        stockout_result.stockout_occurred,
    )

    check(
        "stockout day",
        stockout_result.stockout_day == 0,
        f"got {stockout_result.stockout_day}",
    )

    check(
        "stockout shortage quantity",
        stockout_result.shortage_quantity == 35.0,
        f"got {stockout_result.shortage_quantity}",
    )

    check(
        "stockout ending inventory floored",
        stockout_result.ending_inventory == 0.0,
    )

    check(
        "stockout per-day flag on first day",
        stockout_result.daily_log[0].stockout_occurred,
    )



    replenishment_scenario = _build_test_scenario(
        fixture,
        current_stock=20,
        safety_stock=0.0,
        planning_window_days=3,
        has_incoming_replenishment=True,
        quantity_ordered=20,
    )

    replenishment_world = SimulatedWorld(
        world_id=2,
        daily_demand=[15.0, 15.0, 15.0],
        replenishment_arrival_day=2,
    )

    replenishment_result = simulate_world(
        replenishment_scenario,
        replenishment_world,
    )

    check(
        "in-loop replenishment prevents total depletion",
        replenishment_result.ending_inventory == 5.0,
        f"got {replenishment_result.ending_inventory}",
    )

    check(
        "in-loop replenishment received on arrival day",
        replenishment_result.daily_log[2].replenishment_received == 20.0,
    )

    check(
        "in-loop replenishment stockout before arrival",
        replenishment_result.stockout_occurred
        and replenishment_result.stockout_day == 1,
        f"stockout_day={replenishment_result.stockout_day}",
    )

    check(
        "in-loop replenishment shortage before arrival",
        replenishment_result.shortage_quantity == 10.0,
        f"got {replenishment_result.shortage_quantity}",
    )



    pre_loop_scenario = _build_test_scenario(
        fixture,
        current_stock=10,
        safety_stock=0.0,
        planning_window_days=2,
        has_incoming_replenishment=True,
        quantity_ordered=50,
    )

    pre_loop_world = SimulatedWorld(
        world_id=3,
        daily_demand=[30.0, 30.0],
        replenishment_arrival_day=0,
    )

    pre_loop_result = simulate_world(pre_loop_scenario, pre_loop_world)

    check(
        "pre-loop replenishment ending inventory",
        pre_loop_result.ending_inventory == 0.0,
        f"got {pre_loop_result.ending_inventory}",
    )

    check(
        "pre-loop replenishment not duplicated in daily log",
        all(day.replenishment_received == 0.0 for day in pre_loop_result.daily_log),
    )



    safety_scenario = _build_test_scenario(
        fixture,
        current_stock=20,
        safety_stock=25.0,
        planning_window_days=3,
    )

    safety_world = SimulatedWorld(
        world_id=4,
        daily_demand=[2.0, 2.0, 2.0],
        replenishment_arrival_day=None,
    )

    safety_result = simulate_world(safety_scenario, safety_world)

    check(
        "safety stock breached",
        safety_result.safety_stock_breached,
    )

    check(
        "days below safety stock",
        safety_result.days_below_safety_stock == 3,
        f"got {safety_result.days_below_safety_stock}",
    )

    check(
        "per-day below safety stock flags",
        all(day.below_safety_stock for day in safety_result.daily_log),
    )



    batch_worlds = [
        SimulatedWorld(world_id=index, daily_demand=[5.0, 5.0], replenishment_arrival_day=None)
        for index in range(3)
    ]

    batch_scenario = _build_test_scenario(
        fixture,
        current_stock=20,
        safety_stock=0.0,
        planning_window_days=2,
    )

    batch_results = simulate_worlds(batch_scenario, batch_worlds)

    check(
        "simulate_worlds result count",
        len(batch_results) == 3,
    )

    check(
        "simulate_worlds preserves world_id",
        [result.world_id for result in batch_results] == [0, 1, 2],
    )



    validation_scenario = _build_test_scenario(
        fixture,
        current_stock=10,
        safety_stock=0.0,
        planning_window_days=3,
    )

    validation_world = SimulatedWorld(
        world_id=99,
        daily_demand=[1.0, 1.0],
        replenishment_arrival_day=None,
    )

    validation_error: ValueError | None = None

    try:

        simulate_world(validation_scenario, validation_world)

    except ValueError as exc:

        validation_error = exc



    check(
        "validation rejects mismatched demand length",
        validation_error is not None
        and "daily_demand length" in str(validation_error),
    )



    print()

    if failures:

        print(f"{failures} test(s) failed.")

        return 1

    print("All deterministic Stage 4 tests passed.")

    return 0





def _make_simulation_result(
    world_id: int,
    *,
    ending_inventory: float,
    shortage_quantity: float,
    stockout_occurred: bool = False,
    days_below_safety_stock: int = 0,
    daily_log_len: int = 1,
) -> SimulationResult:
    return SimulationResult(
        world_id=world_id,
        ending_inventory=ending_inventory,
        minimum_inventory=ending_inventory,
        stockout_occurred=stockout_occurred,
        stockout_day=0 if stockout_occurred else None,
        shortage_quantity=shortage_quantity,
        safety_stock_breached=days_below_safety_stock > 0,
        days_below_safety_stock=days_below_safety_stock,
        daily_log=[
            SimulationDay(
                day=0,
                starting_inventory=ending_inventory,
                demand=0.0,
                replenishment_received=0.0,
                ending_inventory=ending_inventory,
                below_safety_stock=False,
                stockout_occurred=stockout_occurred,
            )
        ]
        * daily_log_len,
    )





def run_deterministic_stage5_tests() -> int:

    print_section("Deterministic Stage 5 Tests")

    failures = 0

    fixture = discover_default_fixture()



    def check(name: str, condition: bool, detail: str = "") -> None:

        nonlocal failures

        if condition:

            print(f"  PASS  {name}")

        else:

            failures += 1

            suffix = f" — {detail}" if detail else ""

            print(f"  FAIL  {name}{suffix}")



    portfolio_results = [
        _make_simulation_result(
            0,
            ending_inventory=70.0,
            shortage_quantity=0.0,
            days_below_safety_stock=0,
        ),
        _make_simulation_result(
            1,
            ending_inventory=0.0,
            shortage_quantity=35.0,
            stockout_occurred=True,
            days_below_safety_stock=2,
        ),
        _make_simulation_result(
            2,
            ending_inventory=5.0,
            shortage_quantity=10.0,
            stockout_occurred=True,
            days_below_safety_stock=1,
        ),
        _make_simulation_result(
            3,
            ending_inventory=50.0,
            shortage_quantity=0.0,
            days_below_safety_stock=3,
        ),
    ]

    portfolio_scenario = _build_test_scenario(
        fixture,
        current_stock=100,
        safety_stock=10.0,
        planning_window_days=3,
    )

    portfolio_outcome = discover_outcomes(
        portfolio_scenario,
        portfolio_results,
    )

    check(
        "portfolio stockout probability",
        portfolio_outcome.stockout_probability == 0.5,
        f"got {portfolio_outcome.stockout_probability}",
    )

    check(
        "portfolio avg ending inventory",
        portfolio_outcome.avg_ending_inventory == 31.25,
        f"got {portfolio_outcome.avg_ending_inventory}",
    )

    check(
        "portfolio avg shortage quantity",
        portfolio_outcome.avg_shortage_quantity == 11.25,
        f"got {portfolio_outcome.avg_shortage_quantity}",
    )

    check(
        "portfolio avg days below safety stock",
        portfolio_outcome.avg_days_below_safety_stock == 1.5,
        f"got {portfolio_outcome.avg_days_below_safety_stock}",
    )

    check(
        "best case selects lowest shortage with highest ending inventory",
        portfolio_outcome.best_case_world.world_id == 0,
        f"got world_id={portfolio_outcome.best_case_world.world_id}",
    )

    check(
        "worst case selects highest shortage quantity",
        portfolio_outcome.worst_case_world.world_id == 1,
        f"got world_id={portfolio_outcome.worst_case_world.world_id}",
    )

    check(
        "most likely selects world closest to portfolio averages",
        portfolio_outcome.most_likely_world.world_id == 2,
        f"got world_id={portfolio_outcome.most_likely_world.world_id}",
    )

    check(
        "best case preserves original SimulationResult reference",
        portfolio_outcome.best_case_world is portfolio_results[0],
    )

    check(
        "most likely preserves original SimulationResult reference",
        portfolio_outcome.most_likely_world is portfolio_results[2],
    )

    check(
        "worst case preserves original SimulationResult reference",
        portfolio_outcome.worst_case_world is portfolio_results[1],
    )

    check(
        "portfolio signals exclude high_stockout_risk at exactly 0.5",
        "high_stockout_risk" not in portfolio_outcome.signals,
        f"signals={portfolio_outcome.signals}",
    )

    check(
        "portfolio signals include excess_inventory",
        "excess_inventory" in portfolio_outcome.signals,
        f"signals={portfolio_outcome.signals}",
    )

    check(
        "portfolio signals include late_replenishment_risk",
        "late_replenishment_risk" in portfolio_outcome.signals,
        f"signals={portfolio_outcome.signals}",
    )



    all_signals_results = [
        _make_simulation_result(
            0,
            ending_inventory=100.0,
            shortage_quantity=5.0,
            stockout_occurred=True,
            days_below_safety_stock=2,
        ),
        _make_simulation_result(
            1,
            ending_inventory=90.0,
            shortage_quantity=10.0,
            stockout_occurred=True,
            days_below_safety_stock=1,
        ),
        _make_simulation_result(
            2,
            ending_inventory=80.0,
            shortage_quantity=15.0,
            stockout_occurred=True,
            days_below_safety_stock=1,
        ),
        _make_simulation_result(
            3,
            ending_inventory=70.0,
            shortage_quantity=0.0,
            days_below_safety_stock=0,
        ),
    ]

    all_signals_scenario = _build_test_scenario(
        fixture,
        current_stock=100,
        safety_stock=10.0,
        planning_window_days=3,
    )

    all_signals_outcome = discover_outcomes(
        all_signals_scenario,
        all_signals_results,
    )

    check(
        "all signals triggered when conditions met",
        all_signals_outcome.signals == [
            "high_stockout_risk",
            "excess_inventory",
            "late_replenishment_risk",
        ],
        f"signals={all_signals_outcome.signals}",
    )



    no_signals_results = [
        _make_simulation_result(
            0,
            ending_inventory=10.0,
            shortage_quantity=0.0,
            days_below_safety_stock=0,
        ),
        _make_simulation_result(
            1,
            ending_inventory=12.0,
            shortage_quantity=0.0,
            days_below_safety_stock=0,
        ),
    ]

    no_signals_scenario = _build_test_scenario(
        fixture,
        current_stock=20,
        safety_stock=10.0,
        planning_window_days=2,
    )

    no_signals_outcome = discover_outcomes(
        no_signals_scenario,
        no_signals_results,
    )

    check(
        "no signals when all conditions false",
        no_signals_outcome.signals == [],
        f"signals={no_signals_outcome.signals}",
    )



    empty_error: ValueError | None = None

    try:

        discover_outcomes(portfolio_scenario, [])

    except ValueError as exc:

        empty_error = exc



    check(
        "empty simulation_results raises ValueError",
        empty_error is not None
        and "simulation_results must not be empty" in str(empty_error),
    )



    print()

    if failures:

        print(f"{failures} test(s) failed.")

        return 1

    print("All deterministic Stage 5 tests passed.")

    return 0





def _make_outcome_summary(
    *,
    stockout_probability: float,
    avg_ending_inventory: float,
    avg_shortage_quantity: float,
    avg_days_below_safety_stock: float,
    signals: list[str],
) -> OutcomeSummary:
    sample = _make_simulation_result(
        0,
        ending_inventory=avg_ending_inventory,
        shortage_quantity=avg_shortage_quantity,
        days_below_safety_stock=int(avg_days_below_safety_stock),
    )
    return OutcomeSummary(
        stockout_probability=stockout_probability,
        avg_ending_inventory=avg_ending_inventory,
        avg_shortage_quantity=avg_shortage_quantity,
        avg_days_below_safety_stock=avg_days_below_safety_stock,
        best_case_world=sample,
        most_likely_world=sample,
        worst_case_world=sample,
        signals=signals,
    )





def _make_peer_hub_state(
    base: SimulationState,
    hub_id: str,
    *,
    current_stock: int,
    safety_stock: float,
    coverage_days: float = 10.0,
) -> SimulationState:
    return replace(
        base,
        hub_id=hub_id,
        inventory=replace(
            base.inventory,
            current_stock=current_stock,
            safety_stock=safety_stock,
            coverage_days=coverage_days,
        ),
    )





def run_deterministic_stage6_tests() -> int:
    print_section("Deterministic Stage 6 Tests")

    failures = 0
    fixture = discover_default_fixture()
    base = build_base_state(**fixture)

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"  PASS  {name}")
        else:
            failures += 1
            suffix = f" — {detail}" if detail else ""
            print(f"  FAIL  {name}{suffix}")

    shortage_scenario = _build_test_scenario(
        fixture,
        current_stock=50,
        safety_stock=100.0,
        planning_window_days=3,
    )
    shortage_scenario = replace(
        shortage_scenario,
        replenishment=replace(
            shortage_scenario.replenishment,
            lead_time_days=7,
            actual_delay_days=1,
        ),
    )
    shortage_outcome = _make_outcome_summary(
        stockout_probability=0.5,
        avg_ending_inventory=25.0,
        avg_shortage_quantity=30.0,
        avg_days_below_safety_stock=1.5,
        signals=["late_replenishment_risk"],
    )
    donor_peers = [
        _make_peer_hub_state(
            base,
            "98",
            current_stock=500,
            safety_stock=100.0,
            coverage_days=12.0,
        ),
        _make_peer_hub_state(
            base,
            "99",
            current_stock=400,
            safety_stock=100.0,
            coverage_days=10.0,
        ),
    ]
    shortage_decisions = generate_decisions(
        shortage_scenario,
        shortage_outcome,
        peer_hub_states=donor_peers,
    )
    shortage_types = {decision.decision_type for decision in shortage_decisions}

    check(
        "shortage portfolio generates at least three decisions",
        len(shortage_decisions) >= 3,
        f"count={len(shortage_decisions)}",
    )
    check(
        "shortage portfolio includes expedite replenishment options",
        DecisionType.EXPEDITE_REPLENISHMENT in shortage_types,
        f"types={[d.decision_type.value for d in shortage_decisions]}",
    )
    check(
        "shortage portfolio includes increase safety stock options",
        DecisionType.INCREASE_SAFETY_STOCK in shortage_types,
        f"types={[d.decision_type.value for d in shortage_decisions]}",
    )
    check(
        "shortage portfolio includes inbound inventory transfer",
        any(
            decision.parameters.get("target_hub_id") == shortage_scenario.hub_id
            for decision in shortage_decisions
            if decision.decision_type == DecisionType.INVENTORY_TRANSFER
        ),
        f"decisions={shortage_decisions}",
    )

    excess_scenario = _build_test_scenario(
        fixture,
        current_stock=500,
        safety_stock=100.0,
        planning_window_days=3,
        has_incoming_replenishment=True,
        quantity_ordered=200,
    )
    excess_scenario = replace(
        excess_scenario,
        replenishment=replace(
            excess_scenario.replenishment,
            lead_time_days=7,
            actual_delay_days=0,
        ),
    )
    excess_outcome = _make_outcome_summary(
        stockout_probability=0.05,
        avg_ending_inventory=250.0,
        avg_shortage_quantity=0.0,
        avg_days_below_safety_stock=0.0,
        signals=["excess_inventory"],
    )
    recipient_peers = [
        _make_peer_hub_state(
            base,
            "97",
            current_stock=20,
            safety_stock=100.0,
            coverage_days=1.0,
        ),
        _make_peer_hub_state(
            base,
            "96",
            current_stock=40,
            safety_stock=100.0,
            coverage_days=2.0,
        ),
    ]
    excess_decisions = generate_decisions(
        excess_scenario,
        excess_outcome,
        peer_hub_states=recipient_peers,
    )
    excess_types = {decision.decision_type for decision in excess_decisions}

    check(
        "excess portfolio includes outbound inventory transfer",
        any(
            decision.parameters.get("source_hub_id") == excess_scenario.hub_id
            for decision in excess_decisions
            if decision.decision_type == DecisionType.INVENTORY_TRANSFER
        ),
        f"decisions={excess_decisions}",
    )
    check(
        "excess portfolio includes reduce safety stock options",
        DecisionType.REDUCE_SAFETY_STOCK in excess_types,
        f"types={[d.decision_type.value for d in excess_decisions]}",
    )
    check(
        "excess portfolio includes delay replenishment options",
        DecisionType.DELAY_REPLENISHMENT in excess_types,
        f"types={[d.decision_type.value for d in excess_decisions]}",
    )

    no_trigger_scenario = _build_test_scenario(
        fixture,
        current_stock=100,
        safety_stock=100.0,
        planning_window_days=2,
    )
    no_trigger_outcome = _make_outcome_summary(
        stockout_probability=0.05,
        avg_ending_inventory=15.0,
        avg_shortage_quantity=0.0,
        avg_days_below_safety_stock=0.0,
        signals=[],
    )
    no_trigger_decisions = generate_decisions(
        no_trigger_scenario,
        no_trigger_outcome,
        peer_hub_states=[],
    )
    check(
        "no triggers yields no decisions",
        len(no_trigger_decisions) == 0,
        f"count={len(no_trigger_decisions)}",
    )

    cap_peers = donor_peers + recipient_peers
    cap_scenario = replace(
        shortage_scenario,
        inventory=replace(
            shortage_scenario.inventory,
            current_stock=500,
            safety_stock=100.0,
        ),
        replenishment=replace(
            shortage_scenario.replenishment,
            has_incoming_replenishment=True,
            quantity_ordered=100,
            lead_time_days=7,
            actual_delay_days=0,
        ),
    )
    cap_outcome = _make_outcome_summary(
        stockout_probability=0.05,
        avg_ending_inventory=250.0,
        avg_shortage_quantity=0.0,
        avg_days_below_safety_stock=1.0,
        signals=["excess_inventory", "late_replenishment_risk"],
    )
    cap_decisions = generate_decisions(
        cap_scenario,
        cap_outcome,
        peer_hub_states=cap_peers,
    )
    check(
        "decision list capped at five candidates",
        len(cap_decisions) <= 5,
        f"count={len(cap_decisions)}",
    )

    first_run = generate_decisions(
        shortage_scenario,
        shortage_outcome,
        peer_hub_states=donor_peers,
    )
    second_run = generate_decisions(
        shortage_scenario,
        shortage_outcome,
        peer_hub_states=donor_peers,
    )
    check(
        "decision generation is deterministic",
        [decision.decision_id for decision in first_run]
        == [decision.decision_id for decision in second_run],
        f"first={[d.decision_id for d in first_run]} second={[d.decision_id for d in second_run]}",
    )

    print()
    if failures:
        print(f"{failures} test(s) failed.")
        return 1
    print("All deterministic Stage 6 tests passed.")
    return 0


def run_deterministic_stage7_tests() -> int:
    print_section("Deterministic Stage 7 Tests")

    failures = 0
    fixture = discover_default_fixture()

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"  PASS  {name}")
        else:
            failures += 1
            suffix = f" — {detail}" if detail else ""
            print(f"  FAIL  {name}{suffix}")

    base_scenario = _build_test_scenario(
        fixture,
        current_stock=100,
        safety_stock=100.0,
        planning_window_days=3,
    )
    base_scenario = replace(
        base_scenario,
        replenishment=replace(
            base_scenario.replenishment,
            lead_time_days=10,
            actual_delay_days=2,
        ),
    )

    expedite = Decision(
        decision_id="test_expedite",
        decision_type=DecisionType.EXPEDITE_REPLENISHMENT,
        title="Expedite",
        rationale="test",
        parameters={"lead_time_reduction_days": 5},
    )
    expedited = apply_decision(base_scenario, expedite)
    check(
        "expedite reduces lead time",
        expedited.replenishment.lead_time_days == 5,
        f"lead_time={expedited.replenishment.lead_time_days}",
    )

    expedite_floor = Decision(
        decision_id="test_expedite_floor",
        decision_type=DecisionType.EXPEDITE_REPLENISHMENT,
        title="Expedite floor",
        rationale="test",
        parameters={"lead_time_reduction_days": 20},
    )
    expedited_floor = apply_decision(base_scenario, expedite_floor)
    check(
        "expedite lead time bounded at 1",
        expedited_floor.replenishment.lead_time_days == 1,
        f"lead_time={expedited_floor.replenishment.lead_time_days}",
    )

    increase_ss = Decision(
        decision_id="test_increase_ss",
        decision_type=DecisionType.INCREASE_SAFETY_STOCK,
        title="Increase SS",
        rationale="test",
        parameters={"safety_stock_multiplier": 1.25},
    )
    increased = apply_decision(base_scenario, increase_ss)
    check(
        "increase safety stock multiplies",
        increased.inventory.safety_stock == 125.0,
        f"safety_stock={increased.inventory.safety_stock}",
    )

    reduce_ss = Decision(
        decision_id="test_reduce_ss",
        decision_type=DecisionType.REDUCE_SAFETY_STOCK,
        title="Reduce SS",
        rationale="test",
        parameters={"safety_stock_multiplier": 0.75},
    )
    reduced = apply_decision(base_scenario, reduce_ss)
    check(
        "reduce safety stock multiplies",
        reduced.inventory.safety_stock == 75.0,
        f"safety_stock={reduced.inventory.safety_stock}",
    )

    transfer_in = Decision(
        decision_id="test_transfer_in",
        decision_type=DecisionType.INVENTORY_TRANSFER_IN,
        title="Transfer in",
        rationale="test",
        parameters={"transfer_quantity": 50},
    )
    transferred_in = apply_decision(base_scenario, transfer_in)
    check(
        "inventory transfer in adds stock",
        transferred_in.inventory.current_stock == 150,
        f"current_stock={transferred_in.inventory.current_stock}",
    )

    transfer_out = Decision(
        decision_id="test_transfer_out",
        decision_type=DecisionType.INVENTORY_TRANSFER_OUT,
        title="Transfer out",
        rationale="test",
        parameters={"transfer_quantity": 30},
    )
    transferred_out = apply_decision(base_scenario, transfer_out)
    check(
        "inventory transfer out subtracts stock",
        transferred_out.inventory.current_stock == 70,
        f"current_stock={transferred_out.inventory.current_stock}",
    )

    transfer_out_bad = Decision(
        decision_id="test_transfer_out_bad",
        decision_type=DecisionType.INVENTORY_TRANSFER_OUT,
        title="Transfer out bad",
        rationale="test",
        parameters={"transfer_quantity": 200},
    )
    try:
        apply_decision(base_scenario, transfer_out_bad)
        check("transfer out rejects negative stock", False, "no error raised")
    except ValueError:
        check("transfer out rejects negative stock", True)

    delay = Decision(
        decision_id="test_delay",
        decision_type=DecisionType.DELAY_REPLENISHMENT,
        title="Delay",
        rationale="test",
        parameters={"replenishment_delay_days": 3},
    )
    delayed = apply_decision(base_scenario, delay)
    check(
        "delay replenishment adds delay days",
        delayed.replenishment.actual_delay_days == 5,
        f"actual_delay_days={delayed.replenishment.actual_delay_days}",
    )

    hub_id = str(base_scenario.hub_id)
    transfer_compat_in = Decision(
        decision_id="test_compat_in",
        decision_type=DecisionType.INVENTORY_TRANSFER,
        title="Compat in",
        rationale="test",
        parameters={
            "source_hub_id": "99",
            "target_hub_id": hub_id,
            "transfer_quantity": 25,
        },
    )
    compat_in = apply_decision(base_scenario, transfer_compat_in)
    check(
        "INVENTORY_TRANSFER inbound inferred from target hub",
        compat_in.inventory.current_stock == 125,
        f"current_stock={compat_in.inventory.current_stock}",
    )

    transfer_compat_out = Decision(
        decision_id="test_compat_out",
        decision_type=DecisionType.INVENTORY_TRANSFER,
        title="Compat out",
        rationale="test",
        parameters={
            "source_hub_id": hub_id,
            "target_hub_id": "99",
            "transfer_quantity": 15,
        },
    )
    compat_out = apply_decision(base_scenario, transfer_compat_out)
    check(
        "INVENTORY_TRANSFER outbound inferred from source hub",
        compat_out.inventory.current_stock == 85,
        f"current_stock={compat_out.inventory.current_stock}",
    )

    check(
        "simulate_decisions empty input returns empty list",
        simulate_decisions(base_scenario, []) == [],
    )

    shortage_scenario = _build_test_scenario(
        fixture,
        current_stock=50,
        safety_stock=100.0,
        planning_window_days=3,
    )
    shortage_scenario = replace(
        shortage_scenario,
        replenishment=replace(
            shortage_scenario.replenishment,
            lead_time_days=7,
            actual_delay_days=1,
        ),
        forecast=replace(
            shortage_scenario.forecast,
            forecast_daily=shortage_scenario.forecast.forecast_daily[
                : shortage_scenario.planning_window_days
            ],
        ),
    )
    shortage_outcome = _make_outcome_summary(
        stockout_probability=0.5,
        avg_ending_inventory=25.0,
        avg_shortage_quantity=30.0,
        avg_days_below_safety_stock=1.5,
        signals=["late_replenishment_risk"],
    )
    shortage_decisions = generate_decisions(
        shortage_scenario,
        shortage_outcome,
        peer_hub_states=[],
    )
    selected = shortage_decisions[:2] if len(shortage_decisions) >= 2 else shortage_decisions[:1]
    check(
        "integration has decisions to simulate",
        len(selected) >= 1,
        f"count={len(selected)}",
    )

    if selected:
        sim_results = simulate_decisions(
            shortage_scenario,
            selected,
            n_worlds=1,
            random_seed=42,
            data_dir=DATA_DIR,
        )
        check(
            "simulate_decisions returns one result per decision",
            len(sim_results) == len(selected),
            f"count={len(sim_results)}",
        )
        for result in sim_results:
            outcome = result.outcome
            check(
                f"result for {result.decision.decision_id} has full OutcomeSummary",
                outcome.best_case_world is not None
                and outcome.most_likely_world is not None
                and outcome.worst_case_world is not None
                and 0.0 <= outcome.stockout_probability <= 1.0,
                f"stockout={outcome.stockout_probability}",
            )
            check(
                f"result for {result.decision.decision_id} preserves scenario",
                result.scenario.hub_id == shortage_scenario.hub_id,
            )

    print()
    if failures:
        print(f"{failures} test(s) failed.")
        return 1
    print("All deterministic Stage 7 tests passed.")
    return 0


def _make_test_decision(decision_id: str, title: str = "Test decision") -> Decision:
    return Decision(
        decision_id=decision_id,
        decision_type=DecisionType.INVENTORY_TRANSFER_IN,
        title=title,
        rationale="test",
        parameters={"transfer_quantity": 10},
    )


def _make_decision_simulation_result(
    scenario: ScenarioState,
    decision: Decision,
    outcome: OutcomeSummary,
) -> DecisionSimulationResult:
    return DecisionSimulationResult(
        decision=decision,
        scenario=scenario,
        outcome=outcome,
    )


def run_deterministic_stages_8_11_tests() -> int:
    print_section("Deterministic Stages 8–11 Tests")

    failures = 0
    fixture = discover_default_fixture()

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"  PASS  {name}")
        else:
            failures += 1
            suffix = f" — {detail}" if detail else ""
            print(f"  FAIL  {name}{suffix}")

    scenario = _build_test_scenario(
        fixture,
        current_stock=50,
        safety_stock=100.0,
        planning_window_days=3,
    )
    baseline_outcome = _make_outcome_summary(
        stockout_probability=1.0,
        avg_ending_inventory=10.0,
        avg_shortage_quantity=40.0,
        avg_days_below_safety_stock=2.0,
        signals=["high_stockout_risk"],
    )
    better_outcome = _make_outcome_summary(
        stockout_probability=0.5,
        avg_ending_inventory=30.0,
        avg_shortage_quantity=20.0,
        avg_days_below_safety_stock=1.0,
        signals=[],
    )
    worse_outcome = _make_outcome_summary(
        stockout_probability=1.0,
        avg_ending_inventory=5.0,
        avg_shortage_quantity=50.0,
        avg_days_below_safety_stock=3.0,
        signals=["high_stockout_risk"],
    )

    decision_better = _make_test_decision("decision_better", "Better transfer")
    decision_worse = _make_test_decision("decision_worse", "Worse transfer")
    decision_results = [
        _make_decision_simulation_result(scenario, decision_better, better_outcome),
        _make_decision_simulation_result(scenario, decision_worse, worse_outcome),
    ]

    comparisons = compare_decisions(baseline_outcome, decision_results)
    check("compare_decisions returns one row per result", len(comparisons) == 2)
    better_cmp = comparisons[0]
    check(
        "stockout_probability_change computed",
        better_cmp.stockout_probability_change == -0.5,
        f"value={better_cmp.stockout_probability_change}",
    )
    check(
        "shortage_reduction computed",
        better_cmp.shortage_reduction == 20.0,
        f"value={better_cmp.shortage_reduction}",
    )

    ranked = rank_decisions(comparisons)
    check("rank_decisions assigns ranks", ranked[0].rank == 1 and ranked[1].rank == 2)
    check(
        "better decision ranks first",
        ranked[0].decision.decision_id == "decision_better",
        f"top={ranked[0].decision.decision_id}",
    )
    check(
        "utility scores are descending",
        ranked[0].utility_score >= ranked[1].utility_score,
        f"utility_scores={[item.utility_score for item in ranked]}",
    )
    check(
        "better decision has higher absolute utility",
        ranked[0].utility_score > ranked[1].utility_score,
        f"utility_scores={[item.utility_score for item in ranked]}",
    )

    recommendation = build_recommendation_summary(
        baseline_outcome,
        ranked,
        decision_results,
    )
    check(
        "recommendation picks rank 1",
        recommendation.recommended_decision is not None
        and recommendation.recommended_decision.decision.decision_id == "decision_better",
    )
    check("recommendation has explanation text", bool(recommendation.explanation))

    payload = build_explainability_payload(
        scenario,
        baseline_outcome,
        recommendation,
        ranked,
        decision_results,
    )
    check(
        "payload scenario summary has required keys",
        all(
            key in payload.scenario_summary
            for key in (
                "hub_id",
                "product_id",
                "category",
                "current_stock",
                "safety_stock",
                "predicted_demand",
            )
        ),
    )
    check(
        "baseline summary includes case summaries",
        "case_summaries" in payload.baseline_summary,
    )
    events = payload.best_case_summary.get("key_daily_events", [])
    check(
        "case summary daily events capped",
        len(events) <= 5,
        f"count={len(events)}",
    )
    payload_json = json.dumps(
        {
            "scenario_summary": payload.scenario_summary,
            "baseline_summary": payload.baseline_summary,
            "ranked_decisions_summary": payload.ranked_decisions_summary,
        }
    )
    check(
        "payload excludes full daily logs",
        "daily_log" not in payload_json,
    )

    daily_log = [
        SimulationDay(
            day=1,
            starting_inventory=100.0,
            demand=10.0,
            replenishment_received=0.0,
            ending_inventory=90.0,
            below_safety_stock=False,
            stockout_occurred=False,
        ),
        SimulationDay(
            day=2,
            starting_inventory=90.0,
            demand=95.0,
            replenishment_received=0.0,
            ending_inventory=0.0,
            below_safety_stock=True,
            stockout_occurred=True,
        ),
    ]
    extracted = extract_key_daily_events(daily_log, max_events=5)
    check(
        "daily event extraction prioritizes stockout",
        extracted and extracted[0]["event_type"] == "stockout",
        f"events={extracted}",
    )

    explanation = generate_llm_explanation(payload, skip_llm=True)
    check(
        "template LLM explanation has all sections",
        all(
            getattr(explanation, field)
            for field in (
                "executive_summary",
                "recommended_action",
                "baseline_analysis",
                "decision_comparison",
                "best_case_analysis",
                "most_likely_analysis",
                "worst_case_analysis",
            )
        ),
    )

    selection_request = build_decision_selection_request(
        scenario,
        baseline_outcome,
        [decision_better, decision_worse],
    )
    check(
        "selection request lists candidates",
        len(selection_request.candidate_decisions) == 2,
    )
    resolved = resolve_selected_decisions(
        [decision_better, decision_worse],
        ["decision_better"],
    )
    check(
        "resolve_selected_decisions returns chosen decision",
        len(resolved) == 1 and resolved[0].decision_id == "decision_better",
    )

    base_state = build_base_state(**fixture)
    config = PlanningPipelineConfig(
        base_state=base_state,
        patch=ScenarioPatch(
            planning_window_days=3,
            demand={"demand_multiplier": 1.25},
        ),
        n_worlds=1,
        random_seed=42,
        data_dir=DATA_DIR,
        auto_select_all_decisions=True,
        skip_llm=True,
    )
    full_result = run_full_planning_pipeline(config)
    check(
        "orchestrator produces ranked decisions",
        isinstance(full_result.ranked_decisions, list),
    )
    check(
        "orchestrator produces LLM explanation",
        bool(full_result.llm_explanation.executive_summary),
    )

    baseline = run_baseline_planning(config)
    subset_ids = [d.decision_id for d in baseline.decisions[:1]]
    if subset_ids:
        partial = run_decision_evaluation_and_recommendation(
            baseline,
            subset_ids,
            config,
        )
        check(
            "HITL phase-2 simulates only selected decisions",
            len(partial.decision_results) == len(subset_ids),
            f"count={len(partial.decision_results)}",
        )
    else:
        check("HITL phase-2 has decisions to select", False, "no decisions generated")

    print()
    if failures:
        print(f"{failures} test(s) failed.")
        return 1
    print("All deterministic Stages 8–11 tests passed.")
    return 0





def run_pipeline(

    hub_id: str,

    product_id: str,

    category: str,

    simulation_date: str,

    scenario: str,

    base_state_only: bool,

    stage2_only: bool,

    patch_file: Path | None,

    planning_window_days: int | None,

) -> int:

    print_section("Pipeline Test")

    if not stage2_only:

        print(f"scenario: {scenario}")



    state = build_base_state(

        hub_id=hub_id,

        product_id=product_id,

        category=category,

        simulation_date=simulation_date,

    )

    print_base_state_summary(state)



    if base_state_only:

        print()

        print("Skipped Stage 1 (--base-state-only).")

        return 0



    patch: ScenarioPatch | None = None



    if stage2_only:

        if patch_file is None:

            print()

            print("ERROR: --patch-file is required with --stage2-only.")

            return 1

        patch = load_patch_file(patch_file)

        print_section("Stage 1 - Skipped")

        print(f"patch loaded from {patch_file}")

        print(json.dumps(patch.model_dump(exclude_none=True), indent=2))

    else:

        if not os.environ.get("GROQ_API_KEY"):

            print()

            print("ERROR: GROQ_API_KEY is not set.")

            print(f"Add it to {ENV_FILE} or export it in your shell.")

            return 1



        result = understand_scenario(scenario, state=state)

        print_scenario_result(result)

        if result.status != "complete":

            return 0

        patch = result.patch



    assert patch is not None

    scenario_state = build_scenario_state(

        state,

        patch,

        planning_window_days=planning_window_days,

    )

    print_scenario_state_summary(state, scenario_state)



    worlds = generate_simulated_worlds(

        scenario_state,

        n_worlds=100,

        random_seed=42,

        data_dir=DATA_DIR,

    )

    results = simulate_worlds(scenario_state, worlds)

    print_stage4_summary(results)

    outcome = discover_outcomes(scenario_state, results)

    print_stage5_summary(outcome)

    decisions = generate_decisions(scenario_state, outcome, data_dir=DATA_DIR)

    print_stage6_summary(decisions)

    return 0





def build_parser() -> argparse.ArgumentParser:

    fixture = discover_default_fixture()



    parser = argparse.ArgumentParser(

        description="Test IntelliSupply runtime pipeline (Stages 0–6).",

    )

    parser.add_argument(

        "--scenario",

        default=DEFAULT_SCENARIO,

        help="Natural-language what-if question for Stage 1.",

    )

    parser.add_argument(

        "--compound",

        action="store_true",

        help=f"Use compound scenario: '{DEFAULT_COMPOUND_SCENARIO}'",

    )

    parser.add_argument(

        "--ambiguous",

        action="store_true",

        help=f"Use an ambiguous scenario: '{DEFAULT_AMBIGUOUS_SCENARIO}'",

    )

    parser.add_argument("--hub-id", default=fixture["hub_id"])

    parser.add_argument("--product-id", default=fixture["product_id"])

    parser.add_argument("--category", default=fixture["category"])

    parser.add_argument(

        "--simulation-date",

        default=fixture["simulation_date"],

        help="Use 2024-01-31 to align health data with available forecasts.",

    )

    parser.add_argument(

        "--base-state-only",

        action="store_true",

        help="Run Stage 0 only and skip Stages 1–2.",

    )

    parser.add_argument(

        "--stage2-only",

        action="store_true",

        help="Run Stages 0 and 2 with --patch-file; skip Groq.",

    )

    parser.add_argument(

        "--patch-file",

        type=Path,

        help="JSON file containing a ScenarioPatch for Stage 2.",

    )

    parser.add_argument(

        "--planning-window-days",

        type=int,

        help="Fallback planning horizon when the patch omits planning_window_days.",

    )

    parser.add_argument(

        "--deterministic-stage2",

        action="store_true",

        help="Run built-in Stage 2 patch tests without Groq.",

    )

    parser.add_argument(

        "--deterministic-stage3",

        action="store_true",

        help="Run built-in Stage 3 Monte Carlo tests without Groq.",

    )

    parser.add_argument(

        "--deterministic-stage4",

        action="store_true",

        help="Run built-in Stage 4 baseline DES tests without Groq.",

    )

    parser.add_argument(

        "--deterministic-stage5",

        action="store_true",

        help="Run built-in Stage 5 outcome discovery tests without Groq.",

    )

    parser.add_argument(

        "--deterministic-stage6",

        action="store_true",

        help="Run built-in Stage 6 decision generation tests without Groq.",

    )

    parser.add_argument(

        "--deterministic-stage7",

        action="store_true",

        help="Run built-in Stage 7 decision application and simulation tests without Groq.",

    )

    parser.add_argument(

        "--deterministic-stages8-11",

        action="store_true",

        help="Run built-in Stages 8–11 comparison, ranking, recommendation, and explainability tests.",

    )

    parser.add_argument(

        "--list-fixtures",

        action="store_true",

        help="Print sample hub/product/category fixtures that work with the data.",

    )

    return parser





def main() -> int:

    parser = build_parser()

    args = parser.parse_args()



    if args.list_fixtures:

        print_section("Valid Fixtures")

        for row in list_fixtures():

            print(

                f"hub={row['hub_id']}  product={row['product_id']}  "

                f"category={row['category']}  date={row['simulation_date']}"

            )

        return 0



    if args.deterministic_stage2:

        return run_deterministic_stage2_tests(discover_default_fixture())



    if args.deterministic_stage3:

        return run_deterministic_stage3_tests()



    if args.deterministic_stage4:

        return run_deterministic_stage4_tests()



    if args.deterministic_stage5:

        return run_deterministic_stage5_tests()



    if args.deterministic_stage6:

        return run_deterministic_stage6_tests()



    if args.deterministic_stage7:

        return run_deterministic_stage7_tests()



    if args.deterministic_stages8_11:

        return run_deterministic_stages_8_11_tests()



    if args.compound:

        scenario = DEFAULT_COMPOUND_SCENARIO

    elif args.ambiguous:

        scenario = DEFAULT_AMBIGUOUS_SCENARIO

    else:

        scenario = args.scenario



    return run_pipeline(

        hub_id=args.hub_id,

        product_id=args.product_id,

        category=args.category,

        simulation_date=args.simulation_date,

        scenario=scenario,

        base_state_only=args.base_state_only,

        stage2_only=args.stage2_only,

        patch_file=args.patch_file,

        planning_window_days=args.planning_window_days,

    )





if __name__ == "__main__":

    sys.exit(main())


