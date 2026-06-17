"""Detect missing query entities before RAG execution."""

from __future__ import annotations

from dataclasses import dataclass

from orchestrator.task_registry import QUERY_ENTITY_REQUIREMENTS
from context.clarification_manager import ClarificationManager, ClarificationType


@dataclass
class QueryCompletenessResult:
    complete: bool
    needs_clarification: bool = False
    clarification_type: ClarificationType | None = None
    question: str | None = None
    missing_entities: list[str] | None = None


class QueryCompletenessChecker:
    """Determine whether enough business entities exist for logistics lookups."""

    @staticmethod
    def check(task: str, entities: dict[str, str]) -> QueryCompletenessResult:
        if task == "hub_lookup" and entities.get("hub_id") and not entities.get("city_name"):
            question = ClarificationManager.entity_question(task, ["city_name"])
            return QueryCompletenessResult(
                complete=False,
                needs_clarification=True,
                clarification_type=ClarificationType.ENTITY,
                question=question,
                missing_entities=["city_name"],
            )

        requirements = QUERY_ENTITY_REQUIREMENTS.get(task)
        if not requirements:
            return QueryCompletenessResult(complete=True)

        if any(all(entity in entities for entity in group) for group in requirements):
            return QueryCompletenessResult(complete=True)

        missing = QueryCompletenessChecker._missing_entity_groups(requirements, entities)
        if task == "next_stop_lookup":
            has_courier = bool(entities.get("courier_id")) or entities.get("self_scoped") == "true"
            if has_courier:
                missing = [
                    field
                    for field in ("current_stop", "last_completed_order")
                    if field not in entities
                ]
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
