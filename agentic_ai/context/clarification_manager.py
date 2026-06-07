"""Shared clarification system for intent, entity, and payload gaps."""

from __future__ import annotations

from enum import Enum

# Internal field names that should never be asked of users.
_INTERNAL_FIELDS: frozenset[str] = frozenset({
    "aoi_id",
    "typecode",
    "delivery_user_id",
    "courier_id",
    "rep_dipan_id",
    "from_dipan_id",
    "lat_wgs84",
    "lon_wgs84",
    "receipt_lat_wgs84",
    "receipt_lon_wgs84",
    "receipt_lat",
    "receipt_lng",
    "poi_lat",
    "poi_lng",
    "ds",
    "dataset_kind",
    "granularity",
})

_ENTITY_QUESTIONS: dict[str, str] = {
    "eta_prediction": "Which order would you like the ETA prediction for?",
    "route_prediction": (
        "Which order should I predict the route for, or which hubs "
        "(from and to) should the route connect?"
    ),
    "demand_forecast": "Which city would you like the demand forecast for?",
}

_PAYLOAD_QUESTIONS: dict[str, dict[str, str]] = {
    "eta_prediction": {
        "receipt_time": "When was the package received at the pickup hub?",
    },
    "route_prediction": {
        "receipt_time": "When was the package received at the pickup hub?",
        "delivery_day": "Which delivery day should this route be scheduled for?",
    },
    "demand_forecast": {
        "city": "Which city would you like the demand forecast for?",
        "horizon": "How far ahead should I forecast (e.g. 7 days or 4 weeks)?",
    },
}


class ClarificationType(str, Enum):
    INTENT = "INTENT"
    ENTITY = "ENTITY"
    PAYLOAD = "PAYLOAD"


class ClarificationManager:
    """Generate business-friendly clarification questions."""

    @staticmethod
    def entity_question(task: str, missing_entities: list[str] | None = None) -> str:
        return _ENTITY_QUESTIONS.get(
            task,
            "Could you provide more details so I can look up the shipment?",
        )

    @staticmethod
    def payload_question(task: str, missing_fields: list[str]) -> str:
        user_facing = [
            field for field in missing_fields if field not in _INTERNAL_FIELDS
        ]
        if not user_facing:
            user_facing = missing_fields

        task_questions = _PAYLOAD_QUESTIONS.get(task, {})
        for field in user_facing:
            if field in task_questions:
                return task_questions[field]

        if len(user_facing) == 1:
            return ClarificationManager._generic_field_question(user_facing[0])

        labels = ", ".join(ClarificationManager._label(field) for field in user_facing)
        return f"I still need a few details to run this prediction: {labels}."

    @staticmethod
    def _generic_field_question(field: str) -> str:
        label = ClarificationManager._label(field)
        return f"Could you provide the {label}?"

    @staticmethod
    def _label(field: str) -> str:
        labels = {
            "order_id": "order ID",
            "shipment_id": "shipment ID",
            "receipt_time": "pickup/receipt time",
            "delivery_day": "delivery day",
            "city": "city",
            "horizon": "forecast horizon",
            "from_hub": "origin hub",
            "to_hub": "destination hub",
        }
        return labels.get(field, field.replace("_", " "))
