"""Shared clarification and authorization response categories."""

from __future__ import annotations

from enum import Enum


class ClarificationType(str, Enum):
    DOMAIN = "DOMAIN"
    INTENT = "INTENT"
    ENTITY = "ENTITY"
    AUTHORIZATION = "AUTHORIZATION"


_ENTITY_QUESTIONS: dict[str, str] = {
    "shipment_lookup": "Which shipment, order ID, or courier should I look up?",
    "courier_lookup": "Which courier ID are you asking about?",
    "eta_lookup": "Which order, shipment, or courier should I check the ETA for?",
    "route_lookup": (
        "Which order should I look up the route for, or which hubs "
        "(from and to) should the route connect?"
    ),
    "next_stop_lookup": (
        "What is your current stop, hub, or most recently completed order?"
    ),
    "courier_route_lookup": "Which courier and delivery day should I use for the route?",
    "hub_lookup": "Which city should I list hubs for?",
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
            "shipment status, route, ETA, courier details, or hub/city listings?"
        )
