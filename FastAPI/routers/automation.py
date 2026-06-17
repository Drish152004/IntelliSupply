from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies.auth import TokenUser, require_roles
from automation_policy_store import (
    list_action_audit_logs,
    list_automation_policies,
    upsert_automation_policy,
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
