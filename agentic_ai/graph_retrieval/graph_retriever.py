"""Graph retrieval orchestration for graph-answerable logistics tasks."""

from __future__ import annotations

import logging
from typing import Any

from graph_retrieval.cypher_generator import CypherGenerator
from graph_retrieval.graph_service import GraphService, get_graph_service
from graph_retrieval.result_mapper import ResultMapper

logger = logging.getLogger(__name__)


class GraphRetriever:
    """Generate Cypher, execute against Aura, and detect graph hits."""

    def __init__(self, graph_service: GraphService | None = None) -> None:
        self._graph_service = graph_service or get_graph_service()

    def retrieve(
        self,
        task: str,
        entities: dict[str, str],
    ) -> dict[str, Any]:
        """
        Attempt to answer a task from the graph.

        Returns:
            {"found": true, "result": {...}} or {"found": false}
        """
        if not CypherGenerator.is_graph_answerable(task):
            logger.info("GRAPH MISS\ntask=%s\nreason=not_graph_answerable", task)
            return {"found": False}

        generated = CypherGenerator.generate(task, entities)
        if generated is None:
            logger.info("GRAPH MISS\ntask=%s\nreason=no_cypher", task)
            return {"found": False}

        cypher, parameters = generated
        records = self._graph_service.execute(cypher, parameters)
        logger.info(
            "GRAPH QUERY EXECUTED\ntask=%s\nrecords=%s",
            task,
            len(records),
        )

        mapped = ResultMapper.map_result(task, records)
        if mapped is None:
            logger.info("GRAPH MISS\ntask=%s", task)
            return {"found": False}

        logger.info("GRAPH HIT\ntask=%s", task)
        return {"found": True, "result": mapped}
