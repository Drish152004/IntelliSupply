from __future__ import annotations

from pathlib import Path

import pandas as pd

from base_state import build_base_state
from decision_models import Decision, DecisionType
from simulation_models import OutcomeSummary
from state_models import ScenarioState, SimulationState

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HUBS_CSV = DEFAULT_DATA_DIR / "hubs_simple_import.csv"
MAX_DECISIONS = 5


def _hub_city_id(hub_id: str | int, hubs: pd.DataFrame) -> int | None:
    row = hubs[hubs["hub_id"].astype(str) == str(hub_id)]
    if row.empty:
        return None
    return int(row.iloc[0]["city_id"])


def _high_stockout_risk(outcomes: OutcomeSummary) -> bool:
    return outcomes.stockout_probability > 0.25


def _excess_inventory(outcomes: OutcomeSummary, scenario: ScenarioState) -> bool:
    return (
        "excess_inventory" in outcomes.signals
        or outcomes.avg_ending_inventory > 2 * scenario.inventory.safety_stock
    )


def _frequent_safety_breaches(outcomes: OutcomeSummary) -> bool:
    return outcomes.avg_days_below_safety_stock > 0


def _low_stockout_risk(outcomes: OutcomeSummary) -> bool:
    return outcomes.stockout_probability < 0.10


def _estimated_shortage(outcomes: OutcomeSummary, scenario: ScenarioState) -> float:
    inventory_shortage = max(
        0.0,
        scenario.inventory.safety_stock - scenario.inventory.current_stock,
    )
    return max(outcomes.avg_shortage_quantity, inventory_shortage)


def _projected_shortage(peer: SimulationState) -> float:
    return max(0.0, peer.inventory.safety_stock - peer.inventory.current_stock)


def _donor_excess(peer: SimulationState) -> float:
    return peer.inventory.current_stock - peer.inventory.safety_stock


def _is_donor_hub(peer: SimulationState) -> bool:
    inventory = peer.inventory
    if inventory.current_stock <= inventory.safety_stock:
        return False
    if inventory.coverage_days <= 0:
        return False
    return _donor_excess(peer) > 0


def _is_recipient_hub(peer: SimulationState) -> bool:
    shortage = _projected_shortage(peer)
    return (
        peer.inventory.current_stock < peer.inventory.safety_stock
        or shortage > 0
    )


def _load_peer_hub_states(
    scenario: ScenarioState,
    data_dir: Path,
) -> list[SimulationState]:
    health_path = data_dir / "inventory_health_daily.csv"
    hubs_path = data_dir / "hubs_simple_import.csv"
    health = pd.read_csv(
        health_path,
        usecols=["hub_id", "product_id", "category", "health_date"],
    )
    hubs = pd.read_csv(hubs_path, usecols=["hub_id", "city_id"])
    scenario_city_id = _hub_city_id(scenario.hub_id, hubs)
    if scenario_city_id is None:
        return []

    eligible = health[
        (health["product_id"] == scenario.product_id)
        & (health["category"] == scenario.category)
        & (health["health_date"] <= scenario.simulation_date)
    ]
    if eligible.empty:
        return []

    latest_by_hub = (
        eligible.sort_values("health_date", ascending=False)
        .drop_duplicates(subset=["hub_id"], keep="first")
    )
    same_city_hub_ids = {
        str(hub_id)
        for hub_id in latest_by_hub["hub_id"]
        if _hub_city_id(hub_id, hubs) == scenario_city_id
    }

    current_hub = str(scenario.hub_id)
    peer_states: list[SimulationState] = []
    for hub_id in latest_by_hub["hub_id"]:
        if str(hub_id) == current_hub:
            continue
        if str(hub_id) not in same_city_hub_ids:
            continue
        try:
            peer_states.append(
                build_base_state(
                    str(hub_id),
                    scenario.product_id,
                    scenario.category,
                    scenario.simulation_date,
                )
            )
        except ValueError:
            continue
    return peer_states


def _generate_expedite_decisions(
    scenario: ScenarioState,
    outcomes: OutcomeSummary,
) -> list[Decision]:
    if not (
        _high_stockout_risk(outcomes)
        or "late_replenishment_risk" in outcomes.signals
    ):
        return []
    if scenario.replenishment.lead_time_days is None:
        return []

    decisions: list[Decision] = []
    stockout_pct = outcomes.stockout_probability * 100
    for days in (2, 4):
        decisions.append(
            Decision(
                decision_id=f"expedite_lead_time_{days}",
                decision_type=DecisionType.EXPEDITE_REPLENISHMENT,
                title=f"Expedite replenishment by {days} days",
                rationale=(
                    f"Stockout probability is {stockout_pct:.1f}% "
                    f"and/or late replenishment risk is present; reduce lead time "
                    f"by {days} days to pull inventory in sooner."
                ),
                parameters={"lead_time_reduction_days": days},
            )
        )
    return decisions


def _generate_increase_safety_stock_decisions(
    outcomes: OutcomeSummary,
) -> list[Decision]:
    if not (
        _high_stockout_risk(outcomes) or _frequent_safety_breaches(outcomes)
    ):
        return []

    decisions: list[Decision] = []
    stockout_pct = outcomes.stockout_probability * 100
    breach_days = outcomes.avg_days_below_safety_stock
    for multiplier in (1.25, 1.50):
        multiplier_label = f"{multiplier:.2f}".rstrip("0").rstrip(".")
        decisions.append(
            Decision(
                decision_id=f"increase_safety_stock_{multiplier_label}",
                decision_type=DecisionType.INCREASE_SAFETY_STOCK,
                title=f"Increase safety stock to {multiplier}x current level",
                rationale=(
                    f"Stockout probability is {stockout_pct:.1f}% and average days "
                    f"below safety stock is {breach_days:.1f}; raise safety stock "
                    f"by multiplier {multiplier}."
                ),
                parameters={"safety_stock_multiplier": multiplier},
            )
        )
    return decisions


def _generate_inbound_transfer_decisions(
    scenario: ScenarioState,
    outcomes: OutcomeSummary,
    peer_states: list[SimulationState],
) -> list[Decision]:
    if not _high_stockout_risk(outcomes):
        return []

    estimated_shortage = _estimated_shortage(outcomes, scenario)
    if estimated_shortage <= 0:
        return []

    donors = [peer for peer in peer_states if _is_donor_hub(peer)]
    donors.sort(key=_donor_excess, reverse=True)

    decisions: list[Decision] = []
    for donor in donors[:2]:
        excess = _donor_excess(donor)
        transfer_quantity = int(min(excess, estimated_shortage))
        if transfer_quantity <= 0:
            continue
        decisions.append(
            Decision(
                decision_id=(
                    f"transfer_{donor.hub_id}_to_{scenario.hub_id}_qty_{transfer_quantity}"
                ),
                decision_type=DecisionType.INVENTORY_TRANSFER,
                title=(
                    f"Transfer {transfer_quantity} units from hub "
                    f"{donor.hub_id} to hub {scenario.hub_id}"
                ),
                rationale=(
                    f"Hub {scenario.hub_id} has {outcomes.stockout_probability:.0%} "
                    f"stockout probability with estimated shortage "
                    f"{estimated_shortage:.0f}; hub {donor.hub_id} has "
                    f"{excess:.0f} units of excess inventory."
                ),
                parameters={
                    "source_hub_id": donor.hub_id,
                    "target_hub_id": scenario.hub_id,
                    "transfer_quantity": transfer_quantity,
                },
            )
        )
    return decisions


def _generate_outbound_transfer_decisions(
    scenario: ScenarioState,
    outcomes: OutcomeSummary,
    peer_states: list[SimulationState],
) -> list[Decision]:
    if not _excess_inventory(outcomes, scenario):
        return []

    source_excess = scenario.inventory.current_stock - scenario.inventory.safety_stock
    if source_excess <= 0:
        return []

    recipients = [peer for peer in peer_states if _is_recipient_hub(peer)]
    recipients.sort(key=_projected_shortage, reverse=True)

    decisions: list[Decision] = []
    for recipient in recipients[:2]:
        target_shortage = _projected_shortage(recipient)
        transfer_quantity = int(min(source_excess, target_shortage))
        if transfer_quantity <= 0:
            continue
        decisions.append(
            Decision(
                decision_id=(
                    f"transfer_{scenario.hub_id}_to_{recipient.hub_id}_qty_{transfer_quantity}"
                ),
                decision_type=DecisionType.INVENTORY_TRANSFER,
                title=(
                    f"Transfer {transfer_quantity} units from hub "
                    f"{scenario.hub_id} to hub {recipient.hub_id}"
                ),
                rationale=(
                    f"Hub {scenario.hub_id} has excess inventory "
                    f"({source_excess:.0f} units above safety stock); hub "
                    f"{recipient.hub_id} is below safety stock with projected "
                    f"shortage {target_shortage:.0f}."
                ),
                parameters={
                    "source_hub_id": scenario.hub_id,
                    "target_hub_id": recipient.hub_id,
                    "transfer_quantity": transfer_quantity,
                },
            )
        )
    return decisions


def _generate_reduce_safety_stock_decisions(
    scenario: ScenarioState,
    outcomes: OutcomeSummary,
) -> list[Decision]:
    if not (_low_stockout_risk(outcomes) and _excess_inventory(outcomes, scenario)):
        return []

    decisions: list[Decision] = []
    stockout_pct = outcomes.stockout_probability * 100
    for multiplier in (0.90, 0.75):
        multiplier_label = f"{multiplier:.2f}".rstrip("0").rstrip(".")
        decisions.append(
            Decision(
                decision_id=f"reduce_safety_stock_{multiplier_label}",
                decision_type=DecisionType.REDUCE_SAFETY_STOCK,
                title=f"Reduce safety stock to {multiplier}x current level",
                rationale=(
                    f"Stockout probability is only {stockout_pct:.1f}% while excess "
                    f"inventory is present; lower safety stock multiplier to "
                    f"{multiplier} to release buffer."
                ),
                parameters={"safety_stock_multiplier": multiplier},
            )
        )
    return decisions


def _generate_delay_replenishment_decisions(
    scenario: ScenarioState,
    outcomes: OutcomeSummary,
) -> list[Decision]:
    if not (
        scenario.replenishment.has_incoming_replenishment
        and _excess_inventory(outcomes, scenario)
        and _low_stockout_risk(outcomes)
    ):
        return []

    decisions: list[Decision] = []
    stockout_pct = outcomes.stockout_probability * 100
    for delay_days in (2, 5):
        decisions.append(
            Decision(
                decision_id=f"delay_replenishment_{delay_days}",
                decision_type=DecisionType.DELAY_REPLENISHMENT,
                title=f"Delay incoming replenishment by {delay_days} days",
                rationale=(
                    f"Incoming replenishment exists, excess inventory is present, "
                    f"and stockout probability is {stockout_pct:.1f}%; delay arrival "
                    f"by {delay_days} days to consolidate inventory."
                ),
                parameters={"replenishment_delay_days": delay_days},
            )
        )
    return decisions


def generate_decisions(
    scenario: ScenarioState,
    outcomes: OutcomeSummary,
    *,
    data_dir: Path | None = None,
    peer_hub_states: list[SimulationState] | None = None,
) -> list[Decision]:
    resolved_data_dir = data_dir or DEFAULT_DATA_DIR
    peers = (
        peer_hub_states
        if peer_hub_states is not None
        else _load_peer_hub_states(scenario, resolved_data_dir)
    )

    decisions: list[Decision] = []
    decisions.extend(_generate_expedite_decisions(scenario, outcomes))
    decisions.extend(_generate_increase_safety_stock_decisions(outcomes))
    decisions.extend(
        _generate_inbound_transfer_decisions(scenario, outcomes, peers)
    )
    decisions.extend(
        _generate_outbound_transfer_decisions(scenario, outcomes, peers)
    )
    decisions.extend(_generate_reduce_safety_stock_decisions(scenario, outcomes))
    decisions.extend(_generate_delay_replenishment_decisions(scenario, outcomes))

    return decisions[:MAX_DECISIONS]
