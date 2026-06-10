"""Tests for demand context → HF records adaptation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.adapters.demand_adapter import adapt_demand_payload
from ml.validators import PayloadValidationError

HF_RECORD = {
    "city": "Hangzhou",
    "region_id": "56",
    "day_of_week": 2,
    "month": 11,
    "day_of_month": 5,
    "day_of_year": 309,
    "is_weekend": 0,
    "lag_1": 120.0,
    "lag_2": 115.0,
    "lag_7": 98.0,
    "lag_14": 105.0,
    "rolling_mean_7": 110.0,
    "rolling_std_7": 25.0,
    "rolling_mean_28": 108.0,
}


def test_adapt_demand_payload_extracts_records() -> None:
    result = adapt_demand_payload({"records": [HF_RECORD]})
    assert result == [HF_RECORD]


def test_adapt_demand_payload_rejects_missing_records() -> None:
    with pytest.raises(PayloadValidationError, match="records"):
        adapt_demand_payload({"city": "Shanghai", "horizon": 7})


def test_adapt_demand_payload_rejects_empty_records() -> None:
    with pytest.raises(PayloadValidationError, match="non-empty"):
        adapt_demand_payload({"records": []})
