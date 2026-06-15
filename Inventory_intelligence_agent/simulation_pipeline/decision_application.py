from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from decision_models import Decision, DecisionType
from state_models import ScenarioState


def apply_decision(
    scenario: ScenarioState,
    decision: Decision,
) -> ScenarioState:
    """Apply a single decision to a copy of the scenario and return the modified state."""
    modified = deepcopy(scenario)
    params = decision.parameters

    if decision.decision_type == DecisionType.EXPEDITE_REPLENISHMENT:
        reduction = params.get("lead_time_reduction_days")
        if reduction is None:
            raise ValueError(
                f"EXPEDITE_REPLENISHMENT requires lead_time_reduction_days: {decision.decision_id}"
            )
        lead_time = modified.replenishment.lead_time_days
        if lead_time is None:
            raise ValueError(
                f"Cannot expedite replenishment without lead_time_days: {decision.decision_id}"
            )
        modified.replenishment = replace(
            modified.replenishment,
            lead_time_days=max(1, lead_time - int(reduction)),
        )

    elif decision.decision_type == DecisionType.INCREASE_SAFETY_STOCK:
        multiplier = params.get("safety_stock_multiplier")
        if multiplier is None:
            raise ValueError(
                f"INCREASE_SAFETY_STOCK requires safety_stock_multiplier: {decision.decision_id}"
            )
        modified.inventory = replace(
            modified.inventory,
            safety_stock=modified.inventory.safety_stock * float(multiplier),
        )

    elif decision.decision_type == DecisionType.REDUCE_SAFETY_STOCK:
        multiplier = params.get("safety_stock_multiplier")
        if multiplier is None:
            raise ValueError(
                f"REDUCE_SAFETY_STOCK requires safety_stock_multiplier: {decision.decision_id}"
            )
        modified.inventory = replace(
            modified.inventory,
            safety_stock=modified.inventory.safety_stock * float(multiplier),
        )

    elif decision.decision_type == DecisionType.INVENTORY_TRANSFER_IN:
        quantity = params.get("transfer_quantity")
        if quantity is None:
            raise ValueError(
                f"INVENTORY_TRANSFER_IN requires transfer_quantity: {decision.decision_id}"
            )
        modified.inventory = replace(
            modified.inventory,
            current_stock=modified.inventory.current_stock + int(quantity),
        )

    elif decision.decision_type == DecisionType.INVENTORY_TRANSFER_OUT:
        quantity = params.get("transfer_quantity")
        if quantity is None:
            raise ValueError(
                f"INVENTORY_TRANSFER_OUT requires transfer_quantity: {decision.decision_id}"
            )
        new_stock = modified.inventory.current_stock - int(quantity)
        if new_stock < 0:
            raise ValueError(
                f"INVENTORY_TRANSFER_OUT would make current_stock negative "
                f"({new_stock}): {decision.decision_id}"
            )
        modified.inventory = replace(
            modified.inventory,
            current_stock=new_stock,
        )

    elif decision.decision_type == DecisionType.INVENTORY_TRANSFER:
        source_hub = params.get("source_hub_id")
        target_hub = params.get("target_hub_id")
        quantity = params.get("transfer_quantity")
        if source_hub is None or target_hub is None or quantity is None:
            raise ValueError(
                f"INVENTORY_TRANSFER requires source_hub_id, target_hub_id, "
                f"and transfer_quantity: {decision.decision_id}"
            )
        hub_id = str(modified.hub_id)
        if str(target_hub) == hub_id:
            modified.inventory = replace(
                modified.inventory,
                current_stock=modified.inventory.current_stock + int(quantity),
            )
        elif str(source_hub) == hub_id:
            new_stock = modified.inventory.current_stock - int(quantity)
            if new_stock < 0:
                raise ValueError(
                    f"INVENTORY_TRANSFER out would make current_stock negative "
                    f"({new_stock}): {decision.decision_id}"
                )
            modified.inventory = replace(
                modified.inventory,
                current_stock=new_stock,
            )
        else:
            raise ValueError(
                f"INVENTORY_TRANSFER does not apply to hub {hub_id}: {decision.decision_id}"
            )

    elif decision.decision_type == DecisionType.DELAY_REPLENISHMENT:
        delay_days = params.get("replenishment_delay_days")
        if delay_days is None:
            raise ValueError(
                f"DELAY_REPLENISHMENT requires replenishment_delay_days: {decision.decision_id}"
            )
        actual_delay = modified.replenishment.actual_delay_days
        if actual_delay is None:
            raise ValueError(
                f"Cannot delay replenishment without actual_delay_days: {decision.decision_id}"
            )
        modified.replenishment = replace(
            modified.replenishment,
            actual_delay_days=actual_delay + int(delay_days),
        )

    else:
        raise ValueError(f"Unsupported decision type: {decision.decision_type}")

    return modified
