"""Unit tests for courier-scoped resource authorization."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_retrieval.graph_authorizer import COURIER_SCOPED_TASKS, GraphAuthorizer
from orchestrator.rbac.courier_identity import COURIER_IDENTITY_NOT_BOUND


@pytest.mark.parametrize("task", sorted(COURIER_SCOPED_TASKS))
def test_courier_scoped_tasks_include_logistics_courier_tasks(task: str) -> None:
    assert task in {"route_lookup", "route_prediction", "next_stop_prediction"}


def test_courier_denied_without_bound_identity() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="COURIER",
        task="route_prediction",
        entities={},
        user_query="Predict my route",
        session=None,
    )
    assert allowed is False
    assert reason == COURIER_IDENTITY_NOT_BOUND


def test_courier_denied_other_courier_route_lookup() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="COURIER",
        task="route_lookup",
        entities={"courier_id": "C555"},
        user_query="Show route for courier C555",
        session={"courier_id": "C001"},
    )
    assert allowed is False
    assert "C555" in (reason or "")


def test_courier_allowed_self_scoped_with_session() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="COURIER",
        task="next_stop_prediction",
        entities={"self_scoped": "true"},
        user_query="What is my next stop?",
        session={"courier_id": "C001"},
    )
    assert allowed is True
    assert reason is None


def test_admin_allowed_courier_scoped_task() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="ADMIN",
        task="route_lookup",
        entities={"courier_id": "C999"},
        user_query="Show route for courier C999",
        session=None,
    )
    assert allowed is True
    assert reason is None
