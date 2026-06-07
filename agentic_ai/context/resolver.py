"""Context resolver: graph enrichment, payload building, and readiness checks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from context.clarification_manager import ClarificationManager, ClarificationType
from context.graph_resolver import GraphResolver, get_graph_resolver
from context.missing_field_detector import MissingFieldDetector
from context.payload_builder import PayloadBuilder
from context.task_requirements import is_ml_task, required_fields_for_task

logger = logging.getLogger(__name__)


@dataclass
class ContextResolutionResult:
    ready_for_ml: bool
    payload: dict[str, Any] | None = None
    resolved_context: dict[str, Any] | None = None
    graph_enriched_fields: list[str] | None = None
    user_supplied_fields: list[str] | None = None
    missing_fields: list[str] | None = None
    clarification_needed: bool = False
    clarification_type: ClarificationType | None = None
    clarification_question: str | None = None


class ContextResolver:
    """Resolve graph context, enrich payloads, and determine ML readiness."""

    def __init__(self, graph_resolver: GraphResolver | None = None) -> None:
        self._graph_resolver = graph_resolver or get_graph_resolver()

    def resolve(
        self,
        task: str,
        entities: dict[str, str],
        user_fields: dict[str, Any] | None = None,
    ) -> ContextResolutionResult:
        if not is_ml_task(task):
            return ContextResolutionResult(ready_for_ml=False)

        user_fields = dict(user_fields or {})
        user_fields.update(entities)

        logger.info("GRAPH ENRICHMENT START\ntask=%s\nentities=%s", task, entities)
        graph_context = self._graph_resolver.resolve(task, entities)
        logger.info(
            "GRAPH ENRICHMENT COMPLETE\ntask=%s\nfields=%s",
            task,
            list(graph_context.keys()),
        )

        payload, graph_enriched, user_supplied = PayloadBuilder.build(
            task,
            graph_context,
            user_fields,
        )
        logger.info("PAYLOAD BUILT\ntask=%s\npayload=%s", task, payload)

        required = required_fields_for_task(task)
        missing = MissingFieldDetector.detect(required, payload)
        if missing:
            logger.info("MISSING FIELDS DETECTED\ntask=%s\nmissing=%s", task, missing)
            question = ClarificationManager.payload_question(task, missing)
            logger.info("CLARIFICATION GENERATED\ntype=PAYLOAD\nquestion=%s", question)
            return ContextResolutionResult(
                ready_for_ml=False,
                payload=payload,
                resolved_context={**graph_context, **user_fields},
                graph_enriched_fields=graph_enriched,
                user_supplied_fields=user_supplied,
                missing_fields=missing,
                clarification_needed=True,
                clarification_type=ClarificationType.PAYLOAD,
                clarification_question=question,
            )

        logger.info("READY FOR ML\ntask=%s", task)
        return ContextResolutionResult(
            ready_for_ml=True,
            payload=payload,
            resolved_context={**graph_context, **user_fields},
            graph_enriched_fields=graph_enriched,
            user_supplied_fields=user_supplied,
            missing_fields=[],
            clarification_needed=False,
        )


_resolver: ContextResolver | None = None


def get_context_resolver() -> ContextResolver:
    global _resolver
    if _resolver is None:
        _resolver = ContextResolver()
    return _resolver


def reset_context_resolver(resolver: ContextResolver | None = None) -> None:
    global _resolver
    _resolver = resolver if resolver is not None else ContextResolver()
