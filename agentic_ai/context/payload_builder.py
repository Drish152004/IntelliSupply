"""Build exact ML model payloads from resolved context."""

from __future__ import annotations

from typing import Any

from context.field_source_registry import SYSTEM_DEFAULTS, field_sources_for_task
from context.task_requirements import required_fields_for_task


class PayloadBuilder:
    """Assemble task-specific payloads from graph, user, and default sources."""

    @staticmethod
    def build(
        task: str,
        graph_context: dict[str, Any],
        user_fields: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        """
        Build the ML payload and return (payload, graph_enriched_fields, user_supplied_fields).
        """
        sources = field_sources_for_task(task)
        required = required_fields_for_task(task)
        defaults = SYSTEM_DEFAULTS.get(task, {})

        payload: dict[str, Any] = {}
        graph_enriched: list[str] = []
        user_supplied: list[str] = []

        for field in required:
            source = sources.get(field, "user")
            value = PayloadBuilder._resolve_field(
                field=field,
                source=source,
                graph_context=graph_context,
                user_fields=user_fields,
                defaults=defaults,
            )
            if value is not None and value != "":
                payload[field] = value
                if field in graph_context and graph_context.get(field) == value:
                    graph_enriched.append(field)
                elif field in user_fields and user_fields.get(field) == value:
                    user_supplied.append(field)
                elif source == "system_default":
                    pass
                elif field in graph_context:
                    graph_enriched.append(field)
                elif field in user_fields:
                    user_supplied.append(field)

        if task == "route_prediction":
            PayloadBuilder._apply_route_coordinate_fallback(payload, graph_context)

        if task == "demand_forecast" and "city" not in payload:
            city = user_fields.get("city") or user_fields.get("city_name")
            if city:
                payload["city"] = city
                user_supplied.append("city")

        return payload, sorted(set(graph_enriched)), sorted(set(user_supplied))

    @staticmethod
    def _resolve_field(
        field: str,
        source: str,
        graph_context: dict[str, Any],
        user_fields: dict[str, Any],
        defaults: dict[str, Any],
    ) -> Any:
        if source == "system_default":
            return defaults.get(field)

        if source == "user":
            return user_fields.get(field) or user_fields.get(
                PayloadBuilder._alias(field)
            )

        if source == "user_or_graph":
            user_val = user_fields.get(field)
            if user_val is not None and user_val != "":
                return user_val
            return graph_context.get(field)

        return graph_context.get(field)

    @staticmethod
    def _alias(field: str) -> str:
        if field == "city":
            return "city_name"
        return field

    @staticmethod
    def _apply_route_coordinate_fallback(
        payload: dict[str, Any],
        graph_context: dict[str, Any],
    ) -> None:
        if "receipt_lat_wgs84" not in payload and graph_context.get("receipt_lat_wgs84"):
            payload["receipt_lat_wgs84"] = graph_context["receipt_lat_wgs84"]
        if "receipt_lon_wgs84" not in payload and graph_context.get("receipt_lon_wgs84"):
            payload["receipt_lon_wgs84"] = graph_context["receipt_lon_wgs84"]
