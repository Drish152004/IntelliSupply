from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_models import (
    AutomationPolicy,
    POLICY_TYPE_INVENTORY_TRANSFER,
    POLICY_TYPE_REPLENISHMENT_ORDER,
    POLICY_TYPE_SAFETY_STOCK_CHANGE_PCT,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POLICIES_CSV = DATA_DIR / "automation_policies.csv"
AUDIT_LOG_CSV = DATA_DIR / "action_audit_log.csv"

POLICY_FIELDS = ["policy_type", "enabled", "auto_execute", "threshold_value"]
AUDIT_FIELDS = [
    "timestamp",
    "decision_id",
    "decision_type",
    "decision_parameters",
    "policy_type",
    "execution_status",
    "reason",
    "before_state",
    "after_state",
]

DEFAULT_POLICIES: list[AutomationPolicy] = [
    AutomationPolicy(
        policy_type=POLICY_TYPE_INVENTORY_TRANSFER,
        enabled=True,
        auto_execute=False,
        threshold_value=50.0,
    ),
    AutomationPolicy(
        policy_type=POLICY_TYPE_SAFETY_STOCK_CHANGE_PCT,
        enabled=True,
        auto_execute=False,
        threshold_value=15.0,
    ),
    AutomationPolicy(
        policy_type=POLICY_TYPE_REPLENISHMENT_ORDER,
        enabled=True,
        auto_execute=False,
        threshold_value=2.0,
    ),
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _to_json_value(value: Any) -> str:
    if value is None:
        return ""
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, separators=(",", ":"), default=str)


def ensure_automation_csv_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not POLICIES_CSV.exists():
        with POLICIES_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=POLICY_FIELDS)
            writer.writeheader()
            for policy in DEFAULT_POLICIES:
                writer.writerow(
                    {
                        "policy_type": policy.policy_type,
                        "enabled": str(policy.enabled).lower(),
                        "auto_execute": str(policy.auto_execute).lower(),
                        "threshold_value": policy.threshold_value,
                    }
                )

    if not AUDIT_LOG_CSV.exists():
        with AUDIT_LOG_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
            writer.writeheader()


def list_automation_policies() -> list[AutomationPolicy]:
    ensure_automation_csv_files()
    rows: list[AutomationPolicy] = []
    with POLICIES_CSV.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                AutomationPolicy(
                    policy_type=str(row.get("policy_type", "")).strip(),
                    enabled=_as_bool(row.get("enabled")),
                    auto_execute=_as_bool(row.get("auto_execute")),
                    threshold_value=float(row.get("threshold_value") or 0.0),
                )
            )
    return rows


def get_automation_policy(policy_type: str) -> AutomationPolicy | None:
    for policy in list_automation_policies():
        if policy.policy_type == policy_type:
            return policy
    return None


def upsert_automation_policy(
    policy_type: str,
    enabled: bool,
    auto_execute: bool,
    threshold_value: float,
) -> AutomationPolicy:
    policies = list_automation_policies()
    updated = False

    for idx, policy in enumerate(policies):
        if policy.policy_type == policy_type:
            policies[idx] = AutomationPolicy(
                policy_type=policy_type,
                enabled=bool(enabled),
                auto_execute=bool(auto_execute),
                threshold_value=float(threshold_value),
            )
            updated = True
            break

    if not updated:
        policies.append(
            AutomationPolicy(
                policy_type=policy_type,
                enabled=bool(enabled),
                auto_execute=bool(auto_execute),
                threshold_value=float(threshold_value),
            )
        )

    with POLICIES_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=POLICY_FIELDS)
        writer.writeheader()
        for policy in policies:
            writer.writerow(
                {
                    "policy_type": policy.policy_type,
                    "enabled": str(policy.enabled).lower(),
                    "auto_execute": str(policy.auto_execute).lower(),
                    "threshold_value": policy.threshold_value,
                }
            )

    return get_automation_policy(policy_type) or AutomationPolicy(
        policy_type=policy_type,
        enabled=enabled,
        auto_execute=auto_execute,
        threshold_value=threshold_value,
    )


def append_action_audit_log(
    *,
    decision_id: str,
    decision_type: str,
    decision_parameters: dict[str, Any],
    policy_type: str,
    execution_status: str,
    reason: str,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    ensure_automation_csv_files()
    row = {
        "timestamp": timestamp or _utc_now_iso(),
        "decision_id": decision_id,
        "decision_type": decision_type,
        "decision_parameters": _to_json_value(decision_parameters),
        "policy_type": policy_type,
        "execution_status": execution_status,
        "reason": reason,
        "before_state": _to_json_value(before_state),
        "after_state": _to_json_value(after_state),
    }
    with AUDIT_LOG_CSV.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writerow(row)
    return row


def list_action_audit_logs(
    *,
    limit: int = 100,
    decision_type: str | None = None,
    execution_status: str | None = None,
) -> list[dict[str, Any]]:
    ensure_automation_csv_files()
    rows: list[dict[str, Any]] = []
    with AUDIT_LOG_CSV.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if decision_type and row.get("decision_type") != decision_type:
                continue
            if execution_status and row.get("execution_status") != execution_status:
                continue

            def _decode(payload: str | None) -> Any:
                if not payload:
                    return None
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    return payload

            rows.append(
                {
                    "timestamp": row.get("timestamp"),
                    "decision_id": row.get("decision_id"),
                    "decision_type": row.get("decision_type"),
                    "decision_parameters": _decode(row.get("decision_parameters")),
                    "policy_type": row.get("policy_type"),
                    "execution_status": row.get("execution_status"),
                    "reason": row.get("reason"),
                    "before_state": _decode(row.get("before_state")),
                    "after_state": _decode(row.get("after_state")),
                }
            )

    rows.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
    return rows[: max(1, int(limit))]
