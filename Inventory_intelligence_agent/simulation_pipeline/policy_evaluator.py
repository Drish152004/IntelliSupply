from __future__ import annotations

from decision_models import (
    DECISION_TYPE_TO_POLICY_TYPE,
    Decision,
    ExecutionDecision,
    POLICY_APPROVAL_REQUIRED,
    POLICY_AUTO_APPROVED,
    POLICY_DISABLED,
    POLICY_TYPE_INVENTORY_TRANSFER,
    POLICY_TYPE_REPLENISHMENT_ORDER,
    POLICY_TYPE_SAFETY_STOCK_CHANGE_PCT,
)
from automation_policy_store import get_automation_policy


def _inventory_transfer_value(decision: Decision) -> float:
    return float(decision.parameters.get("transfer_quantity") or 0.0)


def _safety_stock_change_pct_value(decision: Decision) -> float:
    multiplier = float(decision.parameters.get("safety_stock_multiplier") or 1.0)
    return abs((multiplier - 1.0) * 100.0)


def _replenishment_order_value(decision: Decision) -> float:
    if "lead_time_reduction_days" in decision.parameters:
        return float(decision.parameters.get("lead_time_reduction_days") or 0.0)
    return float(decision.parameters.get("replenishment_delay_days") or 0.0)


def _observed_value(policy_type: str, decision: Decision) -> float:
    if policy_type == POLICY_TYPE_INVENTORY_TRANSFER:
        return _inventory_transfer_value(decision)
    if policy_type == POLICY_TYPE_SAFETY_STOCK_CHANGE_PCT:
        return _safety_stock_change_pct_value(decision)
    if policy_type == POLICY_TYPE_REPLENISHMENT_ORDER:
        return _replenishment_order_value(decision)
    return 0.0


def evaluate_policy(
    decision: Decision,
    *,
    utility_score: float | None = None,
) -> ExecutionDecision:
    policy_type = DECISION_TYPE_TO_POLICY_TYPE.get(decision.decision_type)
    if not policy_type:
        return ExecutionDecision(
            decision=decision,
            status=POLICY_APPROVAL_REQUIRED,
            reason="POLICY_TYPE_UNMAPPED",
            policy_type="unknown",
        )

    policy = get_automation_policy(policy_type)
    if policy is None:
        return ExecutionDecision(
            decision=decision,
            status=POLICY_APPROVAL_REQUIRED,
            reason="POLICY_MISSING",
            policy_type=policy_type,
        )

    if not policy.enabled:
        return ExecutionDecision(
            decision=decision,
            status=POLICY_DISABLED,
            reason="POLICY_DISABLED",
            policy_type=policy_type,
            threshold_value=policy.threshold_value,
        )

    if not policy.auto_execute:
        return ExecutionDecision(
            decision=decision,
            status=POLICY_APPROVAL_REQUIRED,
            reason="AUTO_EXECUTE_OFF",
            policy_type=policy_type,
            threshold_value=policy.threshold_value,
            utility_score_threshold=policy.utility_score_threshold,
            observed_utility_score=utility_score,
        )

    if utility_score is not None:
        normalized_utility = float(utility_score) / 100.0
        if normalized_utility < float(policy.utility_score_threshold):
            return ExecutionDecision(
                decision=decision,
                status=POLICY_APPROVAL_REQUIRED,
                reason="BELOW_UTILITY_THRESHOLD",
                policy_type=policy_type,
                threshold_value=policy.threshold_value,
                utility_score_threshold=policy.utility_score_threshold,
                observed_utility_score=utility_score,
            )

    observed = _observed_value(policy_type, decision)
    if observed <= float(policy.threshold_value):
        return ExecutionDecision(
            decision=decision,
            status=POLICY_AUTO_APPROVED,
            reason="WITHIN_THRESHOLD",
            policy_type=policy_type,
            threshold_value=policy.threshold_value,
            observed_value=observed,
            utility_score_threshold=policy.utility_score_threshold,
            observed_utility_score=utility_score,
        )

    return ExecutionDecision(
        decision=decision,
        status=POLICY_APPROVAL_REQUIRED,
        reason="EXCEEDS_THRESHOLD",
        policy_type=policy_type,
        threshold_value=policy.threshold_value,
        observed_value=observed,
        utility_score_threshold=policy.utility_score_threshold,
        observed_utility_score=utility_score,
    )
