"""Tests for demand context → DemandForecastPipeline kwargs adaptation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.adapters.demand_adapter import adapt_demand_payload
from ml.validators import PayloadValidationError, validate_demand_payload

FULL_CONTEXT_PAYLOAD = {
    "city": "Shanghai",
    "horizon": "14",
    "granularity": "daily",
    "dataset_kind": "delivery",
}

PARTIAL_CONTEXT_PAYLOAD = {
    "city": "Shanghai",
    "horizon": "7",
}


def test_adapt_demand_payload_produces_valid_pipeline_schema() -> None:
    result = adapt_demand_payload(FULL_CONTEXT_PAYLOAD)

    assert result["city"] == "Shanghai"
    assert result["horizon"] == 14
    assert result["granularity"] == "daily"
    assert result["dataset_kind"] == "delivery"

    validate_demand_payload(result, schema="pipeline")


def test_adapt_demand_payload_applies_defaults() -> None:
    result = adapt_demand_payload(PARTIAL_CONTEXT_PAYLOAD)

    assert result["granularity"] == "daily"
    assert result["dataset_kind"] == "delivery"
    assert result["horizon"] == 7
    validate_demand_payload(result, schema="pipeline")


def test_adapt_demand_payload_accepts_city_name_alias() -> None:
    result = adapt_demand_payload({"city_name": "Hangzhou", "horizon": 5})
    assert result["city"] == "Hangzhou"
    validate_demand_payload(result, schema="pipeline")


def test_adapt_demand_payload_rejects_missing_horizon() -> None:
    with pytest.raises(PayloadValidationError, match="horizon"):
        adapt_demand_payload({"city": "Shanghai", "granularity": "daily"})


def test_adapt_demand_payload_rejects_missing_city() -> None:
    with pytest.raises(PayloadValidationError, match="city"):
        adapt_demand_payload({"horizon": "7"})


def test_adapt_demand_payload_rejects_horizon_out_of_range() -> None:
    with pytest.raises(PayloadValidationError, match="horizon max"):
        adapt_demand_payload({"city": "Shanghai", "horizon": 99, "granularity": "daily"})
