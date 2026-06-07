"""Inventory sql_bridge tests with mocked dependencies."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from integrations import sql_bridge


def test_is_inventory_domain_positive():
    fake_sg = MagicMock()
    fake_sg.allowed_keywords = ["stock", "warehouse", "inventory"]
    with patch.object(sql_bridge, "_ensure_sql_generator"):
        sys.modules["sql_generator"] = fake_sg
        assert sql_bridge.is_inventory_domain("How much stock is in warehouse A?")


@patch.object(sql_bridge, "_ensure_sql_generator")
def test_ask_inventory_sql_invalid_domain(mock_ensure):
    mock_ensure.return_value = lambda question: "INVALID_DOMAIN_QUERY"
    result = sql_bridge.ask_inventory_sql("What is the weather today?")
    assert result["error"] == "invalid_domain"
    assert result["sql"] is None
