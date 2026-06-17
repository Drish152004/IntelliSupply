"""Shared clarification and authorization response categories."""

from __future__ import annotations

from enum import Enum


class ClarificationType(str, Enum):
    DOMAIN = "DOMAIN"
    INTENT = "INTENT"
    ENTITY = "ENTITY"
    AUTHORIZATION = "AUTHORIZATION"


_ENTITY_QUESTIONS: dict[str, str] = {
    "order_lookup": "Which order ID should I look up?",
    "courier_orders": "Which courier should I check orders for?",
    "courier_route": "Which courier should I use?",
    "hub_route": "Which source and destination hubs should I use?",
}


class ClarificationManager:
    """Generate business-friendly clarification questions."""

    @staticmethod
    def domain_question() -> str:
        return (
            "Could you clarify whether you need inventory/stock information "
            "or logistics help (shipments, routes, ETAs, couriers, or hubs)?"
        )

    @staticmethod
    def entity_question(task: str, missing_entities: list[str] | None = None) -> str:
        return _ENTITY_QUESTIONS.get(
            task,
            "Could you provide more details so I can look up the information?",
        )

    @staticmethod
    def intent_question() -> str:
        return (
            "Could you clarify what you want to do — for example inventory stock, "
            "order details, courier orders, courier route, recent deliveries, "
            "delivery schedules, or hub routes?"
        )
