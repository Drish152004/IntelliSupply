"""Tests for identity resolution through run_orchestrator."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.graph import run_orchestrator
from orchestrator.rbac.courier_identity import resolve_courier_identity
from orchestrator.rbac.exceptions import UnknownIdentityError
from orchestrator.rbac.session_context import restore_user_role


def test_resolve_courier_identity_binds_courier_id() -> None:
    identity = resolve_courier_identity({"role": "courier", "courier_id": "C042"})
    assert identity["user_role"] == "COURIER"
    assert identity["logistics_session"]["courier_id"] == "C042"
    assert identity["logistics_session"]["user_role"] == "COURIER"


def test_resolve_courier_identity_requires_user() -> None:
    with pytest.raises(UnknownIdentityError):
        resolve_courier_identity(None)


def test_restore_user_role_from_session() -> None:
    role = restore_user_role(
        user_role=None,
        logistics_session={"user_role": "logistics_manager"},
        inventory_session=None,
    )
    assert role == "LOGISTICS"


@patch("orchestrator.intent.classify_domain_task")
def test_run_orchestrator_denies_missing_identity(mock_classify: MagicMock) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    result = run_orchestrator("Predict ETA for order ORD1")
    payload = json.loads(result["final_response"])
    assert payload["status"] == "access_denied"
    assert payload["message"] == "User identity not provided"


@patch("orchestrator.intent.classify_domain_task")
def test_run_orchestrator_authenticated_user_propagates_role(
    mock_classify: MagicMock,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.95,
    }
    result = run_orchestrator(
        "Optimize my delivery route",
        authenticated_user={"role": "courier", "courier_id": "C001"},
    )
    assert result["user_role"] == "COURIER"
    assert result["logistics_session"]["courier_id"] == "C001"
