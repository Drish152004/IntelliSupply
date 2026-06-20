from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies.auth import TokenUser, require_roles
from action_executors import execute_decision
from automation_execute import decision_from_payload, scenario_from_payload
from automation_policy_store import (
    append_action_audit_log,
    list_action_audit_logs,
    list_automation_policies,
    upsert_automation_policy,
)
from decision_models import (
    DECISION_TYPE_TO_POLICY_TYPE,
    MANUAL_EXECUTED,
    MANUAL_EXECUTION_FAILED,
)

router = APIRouter(prefix="/automation", tags=["automation"])

AutomationUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "inventory_manager")),
]


class UpdateAutomationPolicyRequest(BaseModel):
    enabled: bool
    auto_execute: bool
    threshold_value: float = Field(..., ge=0)


class ExecuteDecisionRequest(BaseModel):
    decision: dict[str, Any]
    scenario: dict[str, Any]


@router.get("/policies")
def get_automation_policies(current_user: AutomationUser):
    del current_user
    return {"policies": [policy.__dict__ for policy in list_automation_policies()]}


@router.put("/policies/{policy_type}")
def update_automation_policy(
    policy_type: str,
    body: UpdateAutomationPolicyRequest,
    current_user: AutomationUser,
):
    del current_user
    try:
        policy = upsert_automation_policy(
            policy_type=policy_type,
            enabled=body.enabled,
            auto_execute=body.auto_execute,
            threshold_value=body.threshold_value,
        )
        return {"policy": policy.__dict__}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {exc}") from exc


@router.get("/audit-logs")
def get_action_audit_logs(
    current_user: AutomationUser,
    limit: int = Query(default=100, ge=1, le=1000),
    decision_type: str | None = Query(default=None),
    execution_status: str | None = Query(default=None),
):
    del current_user
    try:
        logs: list[dict[str, Any]] = list_action_audit_logs(
            limit=limit,
            decision_type=decision_type,
            execution_status=execution_status,
        )
        return {"logs": logs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit logs: {exc}") from exc


@router.post("/execute")
def execute_planning_decision(
    body: ExecuteDecisionRequest,
    current_user: AutomationUser,
):
    del current_user
    try:
        decision = decision_from_payload(body.decision)
        scenario = scenario_from_payload(body.scenario)
        execution_result = execute_decision(decision, scenario)

        policy_type = DECISION_TYPE_TO_POLICY_TYPE.get(decision.decision_type, "unknown")
        execution_status = (
            MANUAL_EXECUTED if execution_result.success else MANUAL_EXECUTION_FAILED
        )
        audit_log = append_action_audit_log(
            decision_id=decision.decision_id,
            decision_type=decision.decision_type.value,
            decision_parameters=decision.parameters,
            policy_type=policy_type,
            execution_status=execution_status,
            reason="USER_APPROVED",
            before_state=execution_result.execution_details.get("before_state"),
            after_state=execution_result.execution_details.get("after_state")
            or execution_result.execution_details,
        )

        return {
            "execution_result": {
                "decision": {
                    "decision_id": execution_result.decision.decision_id,
                    "decision_type": execution_result.decision.decision_type.value,
                    "title": execution_result.decision.title,
                    "rationale": execution_result.decision.rationale,
                    "parameters": execution_result.decision.parameters,
                },
                "success": execution_result.success,
                "execution_details": execution_result.execution_details,
            },
            "audit_log": audit_log,
        }
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid execute payload: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to execute decision: {exc}") from exc
