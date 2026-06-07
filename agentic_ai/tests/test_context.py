"""Unit tests for the context resolution layer (Phase 5)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from context.clarification_manager import ClarificationManager, ClarificationType
from context.entity_extractor import EntityExtractor
from context.graph_resolver import GraphResolver, reset_graph_resolver
from context.missing_field_detector import MissingFieldDetector
from context.payload_builder import PayloadBuilder
from context.query_completeness_checker import QueryCompletenessChecker
from context.resolver import ContextResolver, reset_context_resolver
from context.task_requirements import required_fields_for_task


def test_entity_extractor_order_id() -> None:
    entities = EntityExtractor.extract("What is ETA for order ORD123?")
    assert entities["order_id"] == "ORD123"


def test_entity_extractor_from_to_hub() -> None:
    entities = EntityExtractor.extract("Generate route from Hub_1 to Hub_5")
    assert entities["from_hub"] == "Hub_1"
    assert entities["to_hub"] == "Hub_5"


def test_entity_extractor_city_for_demand() -> None:
    entities = EntityExtractor.extract("Forecast delivery demand in Shanghai")
    assert entities["city_name"] == "Shanghai"
    assert entities["city"] == "Shanghai"


def test_entity_extractor_horizon() -> None:
    entities = EntityExtractor.extract("Forecast demand in Shanghai for next 14 days")
    assert entities["horizon"] == "14"
    assert entities["granularity"] == "daily"


def test_query_completeness_eta_missing_order() -> None:
    result = QueryCompletenessChecker.check("eta_prediction", {})
    assert result.complete is False
    assert result.needs_clarification is True
    assert result.clarification_type == ClarificationType.ENTITY
    assert "order" in result.question.lower()


def test_query_completeness_eta_with_order() -> None:
    result = QueryCompletenessChecker.check(
        "eta_prediction",
        {"order_id": "ORD123"},
    )
    assert result.complete is True


def test_query_completeness_demand_missing_city() -> None:
    result = QueryCompletenessChecker.check("demand_forecast", {})
    assert result.complete is False
    assert result.clarification_type == ClarificationType.ENTITY


def test_query_completeness_route_with_hubs() -> None:
    result = QueryCompletenessChecker.check(
        "route_prediction",
        {"from_hub": "Hub_1", "to_hub": "Hub_5"},
    )
    assert result.complete is True


def test_query_completeness_skips_non_ml_task() -> None:
    result = QueryCompletenessChecker.check("eta_lookup", {})
    assert result.complete is True


def test_missing_field_detector() -> None:
    required = required_fields_for_task("eta_prediction")
    missing = MissingFieldDetector.detect(required, {"order_id": "ORD123"})
    assert "delivery_user_id" in missing
    assert "receipt_time" in missing


def test_clarification_manager_never_asks_internal_fields() -> None:
    question = ClarificationManager.payload_question(
        "eta_prediction",
        ["aoi_id", "receipt_time"],
    )
    assert "aoi_id" not in question.lower()
    assert "received" in question.lower()


def test_payload_builder_demand_forecast_defaults() -> None:
    payload, graph_fields, user_fields = PayloadBuilder.build(
        "demand_forecast",
        graph_context={},
        user_fields={"city": "Shanghai"},
    )
    assert payload["city"] == "Shanghai"
    assert payload["granularity"] == "daily"
    assert payload["dataset_kind"] == "delivery"
    assert "horizon" not in payload
    assert "city" in user_fields
    assert graph_fields == []


def test_payload_builder_eta_from_graph() -> None:
    graph_context = {
        "delivery_user_id": "C001",
        "from_dipan_id": "42",
        "aoi_id": "7",
        "receipt_lat": 30.6,
        "receipt_lng": 104.0,
        "poi_lat": 30.61,
        "poi_lng": 104.01,
        "receipt_time": "2026-06-05T12:00:00",
    }
    payload, graph_fields, _ = PayloadBuilder.build(
        "eta_prediction",
        graph_context=graph_context,
        user_fields={},
    )
    assert payload["delivery_user_id"] == "C001"
    assert payload["receipt_time"] == "2026-06-05T12:00:00"
    assert "delivery_user_id" in graph_fields


def test_graph_resolver_order_lookup() -> None:
    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {
            "order_id": "ORD123",
            "delivery_user_id": "C001",
            "from_dipan_id": "42",
            "aoi_id": "7",
            "receipt_lat": 30.6,
            "receipt_lng": 104.0,
            "poi_lat": 30.61,
            "poi_lng": 104.01,
            "receipt_time": "2026-06-05T12:00:00",
            "lat_wgs84": 30.61,
            "lon_wgs84": 104.01,
            "city_name": "Shanghai",
            "ds": 318,
            "typecode": "T1",
            "delivery_day": "Monday",
        }
    ]
    resolver = GraphResolver(graph_service=mock_service)
    result = resolver.resolve("eta_prediction", {"order_id": "ORD123"})
    assert result["delivery_user_id"] == "C001"
    assert result["from_dipan_id"] == "42"
    mock_service.execute.assert_called_once()


def test_context_resolver_ready_for_ml() -> None:
    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {
            "delivery_user_id": "C001",
            "from_dipan_id": "42",
            "aoi_id": "7",
            "receipt_lat": 30.6,
            "receipt_lng": 104.0,
            "poi_lat": 30.61,
            "poi_lng": 104.01,
            "receipt_time": "2026-06-05T12:00:00",
        }
    ]
    resolver = ContextResolver(graph_resolver=GraphResolver(graph_service=mock_service))
    result = resolver.resolve("eta_prediction", {"order_id": "ORD123"})
    assert result.ready_for_ml is True
    assert result.payload is not None
    assert result.missing_fields == []
    assert "delivery_user_id" in result.graph_enriched_fields


def test_context_resolver_payload_clarification() -> None:
    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {
            "delivery_user_id": "C001",
            "from_dipan_id": "42",
            "aoi_id": "7",
            "receipt_lat": 30.6,
            "receipt_lng": 104.0,
            "poi_lat": 30.61,
            "poi_lng": 104.01,
        }
    ]
    resolver = ContextResolver(graph_resolver=GraphResolver(graph_service=mock_service))
    result = resolver.resolve("eta_prediction", {"order_id": "ORD123"})
    assert result.ready_for_ml is False
    assert result.clarification_needed is True
    assert result.clarification_type == ClarificationType.PAYLOAD
    assert "receipt_time" in result.missing_fields
    assert result.clarification_question is not None


def test_context_resolver_demand_forecast_ready() -> None:
    resolver = ContextResolver(graph_resolver=GraphResolver(graph_service=MagicMock()))
    result = resolver.resolve(
        "demand_forecast",
        {"city": "Shanghai", "horizon": "14"},
    )
    assert result.ready_for_ml is True
    assert result.payload["city"] == "Shanghai"
    assert result.payload["horizon"] == "14"


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    reset_graph_resolver()
    reset_context_resolver()
    yield
    reset_graph_resolver()
    reset_context_resolver()
