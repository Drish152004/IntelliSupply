"""Detect missing query entities before graph search (HITL #1)."""

from __future__ import annotations

from dataclasses import dataclass

from context.clarification_manager import ClarificationManager, ClarificationType
from context.task_requirements import QUERY_ENTITY_REQUIREMENTS, is_ml_task


@dataclass
class QueryCompletenessResult:
    complete: bool
    needs_clarification: bool = False
    clarification_type: ClarificationType | None = None
    question: str | None = None
    missing_entities: list[str] | None = None


class QueryCompletenessChecker:
    """Determine whether enough business entities exist to search the graph."""

    @staticmethod
    def check(task: str, entities: dict[str, str]) -> QueryCompletenessResult:
        if not is_ml_task(task):
            return QueryCompletenessResult(complete=True)

        requirements = QUERY_ENTITY_REQUIREMENTS.get(task)
        if not requirements:
            return QueryCompletenessResult(complete=True)

        if any(all(entity in entities for entity in group) for group in requirements):
            return QueryCompletenessResult(complete=True)

        missing = QueryCompletenessChecker._missing_entity_groups(requirements, entities)
        question = ClarificationManager.entity_question(task, missing)
        return QueryCompletenessResult(
            complete=False,
            needs_clarification=True,
            clarification_type=ClarificationType.ENTITY,
            question=question,
            missing_entities=missing,
        )

    @staticmethod
    def _missing_entity_groups(
        requirements: tuple[tuple[str, ...], ...],
        entities: dict[str, str],
    ) -> list[str]:
        missing: list[str] = []
        for group in requirements:
            for entity in group:
                if entity not in entities and entity not in missing:
                    missing.append(entity)
        return missing
