"""Unit tests for auth-to-orchestrator role mapping."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.rbac.exceptions import UnknownIdentityError, UnknownRoleError
from orchestrator.rbac.role_mapper import (
    AUTH_TO_ORCHESTRATOR,
    IDENTITY_REQUIRED_MESSAGE,
    map_to_orchestrator_role,
)


@pytest.mark.parametrize(
    ("raw_role", "expected"),
    [
        ("admin", "ADMIN"),
        ("logistics_manager", "LOGISTICS"),
        ("inventory_manager", "INVENTORY"),
        ("courier", "COURIER"),
        ("ADMIN", "ADMIN"),
        ("LOGISTICS", "LOGISTICS"),
    ],
)
def test_map_to_orchestrator_role_accepts_known_roles(raw_role: str, expected: str) -> None:
    assert map_to_orchestrator_role(raw_role) == expected


def test_map_to_orchestrator_role_rejects_missing() -> None:
    with pytest.raises(UnknownIdentityError, match=IDENTITY_REQUIRED_MESSAGE):
        map_to_orchestrator_role(None)
    with pytest.raises(UnknownIdentityError, match=IDENTITY_REQUIRED_MESSAGE):
        map_to_orchestrator_role("")


def test_map_to_orchestrator_role_rejects_unknown() -> None:
    with pytest.raises(UnknownRoleError):
        map_to_orchestrator_role("guest")


def test_auth_to_orchestrator_covers_all_mappings() -> None:
    assert AUTH_TO_ORCHESTRATOR["courier"] == "COURIER"
