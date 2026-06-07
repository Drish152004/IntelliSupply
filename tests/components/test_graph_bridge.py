"""Graph bridge tests with mocked GraphRAG."""

from __future__ import annotations

from unittest.mock import patch

from integrations import graph_bridge


def test_is_graph_sufficient_with_data():
    response = {
        "result": [{"city": "Shanghai", "hub_count": 3}],
        "answer": "Shanghai has 3 active hubs.",
    }
    assert graph_bridge.is_graph_sufficient(response) is True


def test_is_graph_sufficient_empty_result():
    response = {"result": [], "answer": "No matching data was found."}
    assert graph_bridge.is_graph_sufficient(response) is False


@patch("integrations.graph_bridge._ensure_graph_rag")
def test_try_graph_answer_success(mock_ensure):
    mock_response = {
        "result": [{"courier_id": "C001"}],
        "answer": "Courier C001 is assigned to cluster 4.",
    }
    with patch("graphdb.graph_rag.ask_graph", return_value=mock_response):
        used, response, error = graph_bridge.try_graph_answer("Which courier serves cluster 4?")
    assert used is True
    assert response == mock_response
    assert error is None
