"""Unit tests for the graph retrieval layer."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_retrieval.cypher_generator import CypherGenerator, GRAPH_SCHEMA
from graph_retrieval.entity_extractor import EntityExtractor
from graph_retrieval.graph_authorizer import GraphAuthorizer
from graph_retrieval.graph_retriever import GraphRetriever
from graph_retrieval.graph_service import GraphService, reset_graph_service
from graph_retrieval.result_mapper import ResultMapper


def test_entity_extractor_order_id() -> None:
    entities = EntityExtractor.extract("What is ETA for order ORD123?")
    assert entities["order_id"] == "ORD123"


def test_entity_extractor_courier_id() -> None:
    entities = EntityExtractor.extract("Show route for courier C001")
    assert entities["courier_id"] == "C001"


def test_entity_extractor_shipment_id() -> None:
    entities = EntityExtractor.extract("Track shipment SHIP42 status")
    assert entities["shipment_id"] == "SHIP42"


def test_entity_extractor_self_scoped() -> None:
    entities = EntityExtractor.extract("Show my route")
    assert entities["self_scoped"] == "true"


def test_graph_authorizer_admin_allowed() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="ADMIN",
        task="route_lookup",
        entities={"courier_id": "C555"},
        user_query="Show route for courier C555",
        session={"courier_id": "C001"},
    )
    assert allowed is True
    assert reason is None


def test_graph_authorizer_courier_denied_other_courier() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="COURIER",
        task="route_lookup",
        entities={"courier_id": "C555"},
        user_query="Show route for courier C555",
        session={"courier_id": "C001"},
    )
    assert allowed is False
    assert reason is not None
    assert "C555" in reason


def test_graph_authorizer_courier_denied_without_bound_identity() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="COURIER",
        task="route_lookup",
        entities={"self_scoped": "true"},
        user_query="Show my route",
        session=None,
    )
    assert allowed is False
    assert reason == "Courier identity not bound"


def test_graph_authorizer_courier_allowed_self_route() -> None:
    allowed, reason = GraphAuthorizer.check(
        role="COURIER",
        task="route_lookup",
        entities={"self_scoped": "true"},
        user_query="Show my route",
        session={"courier_id": "C001"},
    )
    assert allowed is True
    assert reason is None


def test_graph_authorizer_resolves_session_courier_id() -> None:
    entities = GraphAuthorizer.resolve_courier_id(
        entities={"self_scoped": "true"},
        user_query="Show my route",
        session={"courier_id": "C001"},
    )
    assert entities["courier_id"] == "C001"


def test_cypher_generator_eta_lookup() -> None:
    generated = CypherGenerator.generate(
        "eta_lookup",
        {"order_id": "ORD123"},
        GRAPH_SCHEMA,
    )
    assert generated is not None
    cypher, parameters = generated
    assert "HAS_ETA" in cypher
    assert "ETAPrediction" in cypher
    assert parameters == {"order_id": "ORD123"}


def test_cypher_generator_route_lookup() -> None:
    generated = CypherGenerator.generate(
        "route_lookup",
        {"courier_id": "C001"},
        GRAPH_SCHEMA,
    )
    assert generated is not None
    cypher, parameters = generated
    assert "RoutePrediction" in cypher
    assert "FOR_COURIER" in cypher
    assert parameters == {"courier_id": "C001"}


def test_cypher_generator_rejects_write_operations() -> None:
    from graph_retrieval.cypher_generator import _validate_read_only

    with pytest.raises(ValueError):
        _validate_read_only("CREATE (n:Order) RETURN n")


def test_result_mapper_eta_lookup() -> None:
    mapped = ResultMapper.map_result(
        "eta_lookup",
        [{"order_id": "ORD123", "eta_minutes": 28, "model_version": "v1"}],
    )
    assert mapped == {
        "order_id": "ORD123",
        "eta_minutes": 28,
        "model_version": "v1",
    }


def test_result_mapper_route_lookup() -> None:
    mapped = ResultMapper.map_result(
        "route_lookup",
        [
            {
                "courier_id": "C001",
                "route_prediction_id": "C001_318_Monday",
                "predicted_sequence": ["ORD1", "ORD2"],
                "stops": [
                    {
                        "order_id": "ORD1",
                        "sequence": 1,
                        "lat_wgs84": 1.1,
                        "lon_wgs84": 2.2,
                    }
                ],
            }
        ],
    )
    assert mapped is not None
    assert mapped["courier_id"] == "C001"
    assert mapped["route"][0]["order_id"] == "ORD1"


def test_graph_retriever_hit_and_miss() -> None:
    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {"order_id": "ORD123", "eta_minutes": 28, "model_version": "v1"}
    ]
    retriever = GraphRetriever(graph_service=mock_service)

    hit = retriever.retrieve("eta_lookup", {"order_id": "ORD123"})
    assert hit["found"] is True
    assert hit["result"]["eta_minutes"] == 28

    mock_service.execute.return_value = []
    miss = retriever.retrieve("eta_lookup", {"order_id": "ORD999"})
    assert miss["found"] is False


def test_graph_service_graceful_failure() -> None:
    mock_connection = MagicMock()
    mock_connection.execute_query.side_effect = ConnectionError("Aura unavailable")
    service = GraphService(connection=mock_connection)
    assert service.execute("RETURN 1", {}) == []


@pytest.fixture(autouse=True)
def _reset_graph_service() -> None:
    reset_graph_service()
    yield
    reset_graph_service()
