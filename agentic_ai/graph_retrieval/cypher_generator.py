"""Cypher generation for graph-answerable logistics lookup tasks."""

from __future__ import annotations

import logging
import re
from typing import Any

from integrations.llm_client import get_client, get_model

logger = logging.getLogger(__name__)

GRAPH_SCHEMA = """
Allowed Nodes:
City
Hub
Courier
Role
Order
Notes
RoutePrediction
ETAPrediction

Allowed Relationships:
LOCATED_IN
HAS_ROLE
OPERATES_IN
ASSIGNED_TO_HUB
FROM_HUB
TO_HUB
BELONGS_TO_CITY
ASSIGNED_TO
HAS_NOTES
FOR_COURIER
STARTS_FROM
HAS_ETA
HAS_STOP
"""

GRAPH_ANSWERABLE_TASKS: frozenset[str] = frozenset({
    "shipment_lookup",
    "courier_lookup",
    "route_lookup",
    "eta_lookup",
})

_WRITE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|CALL\s+\{)\b",
    re.I,
)

_TASK_TEMPLATES: dict[str, tuple[str, tuple[str, ...]]] = {
    "eta_lookup": (
        """
        MATCH (o:Order {order_id: $order_id})-[:HAS_ETA]->(e:ETAPrediction)
        RETURN
            o.order_id AS order_id,
            e.eta_minutes AS eta_minutes,
            e.model_version AS model_version,
            e.created_at AS created_at
        LIMIT 1
        """.strip(),
        ("order_id",),
    ),
    "route_lookup": (
        """
        MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier {courier_id: $courier_id})
        OPTIONAL MATCH (rp)-[stop:HAS_STOP]->(o:Order)
        WITH rp, c, stop, o
        ORDER BY stop.sequence ASC
        RETURN
            rp.route_prediction_id AS route_prediction_id,
            c.courier_id AS courier_id,
            rp.predicted_sequence AS predicted_sequence,
            rp.city_name AS city_name,
            rp.delivery_day AS delivery_day,
            collect({
                order_id: o.order_id,
                sequence: stop.sequence,
                lat_wgs84: stop.lat_wgs84,
                lon_wgs84: stop.lon_wgs84
            }) AS stops
        ORDER BY rp.updated_at DESC
        LIMIT 1
        """.strip(),
        ("courier_id",),
    ),
    "courier_lookup": (
        """
        MATCH (c:Courier {courier_id: $courier_id})
        OPTIONAL MATCH (c)-[:OPERATES_IN]->(city:City)
        OPTIONAL MATCH (c)-[:HAS_ROLE]->(r:Role)
        RETURN
            c.courier_id AS courier_id,
            c.name AS name,
            c.email AS email,
            c.hub_id AS hub_id,
            c.hub_name AS hub_name,
            coalesce(city.city_name, c.city_name) AS city_name,
            r.role_name AS role_name
        LIMIT 1
        """.strip(),
        ("courier_id",),
    ),
    "shipment_lookup": (
        """
        MATCH (o:Order {order_id: $shipment_id})
        OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(c:Courier)
        OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
        OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)
        RETURN
            o.order_id AS order_id,
            o.city_name AS city_name,
            o.delivery_day AS delivery_day,
            o.receipt_time AS receipt_time,
            c.courier_id AS courier_id,
            c.name AS courier_name,
            coalesce(fromHub.name, o.from_hub_name) AS from_hub,
            coalesce(toHub.name, o.to_hub_name) AS to_hub,
            o.assigned_courier_id AS assigned_courier_id
        LIMIT 1
        """.strip(),
        ("shipment_id",),
    ),
}


def _normalize_cypher(cypher: str) -> str:
    return re.sub(r"\s+", " ", cypher.strip())


def _is_valid_shipment_reference(value: str) -> bool:
    cleaned = value.strip()
    if len(cleaned) < 3:
        return False
    if cleaned.lower() in {"s", "sh", "ship", "shipment", "shipments"}:
        return False
    return True


def _validate_read_only(cypher: str) -> None:
    if _WRITE_PATTERN.search(cypher):
        raise ValueError("Generated Cypher contains write operations.")


class CypherGenerator:
    """Generate parameterized Cypher for graph-answerable tasks."""

    @staticmethod
    def is_graph_answerable(task: str) -> bool:
        return task in GRAPH_ANSWERABLE_TASKS

    @staticmethod
    def generate(
        task: str,
        entities: dict[str, str],
        schema: str | None = None,
        *,
        use_llm: bool = False,
    ) -> tuple[str, dict[str, Any]] | None:
        """
        Return (cypher, parameters) for a graph lookup, or None when unsupported.

        Uses deterministic templates by default. Optional LLM generation is only
        attempted when templates cannot be built.
        """
        template_result = CypherGenerator._from_template(task, entities)
        if template_result is not None:
            return template_result

        if not use_llm:
            return None

        return CypherGenerator._from_llm(task, entities, schema or GRAPH_SCHEMA)

    @staticmethod
    def _from_template(
        task: str,
        entities: dict[str, str],
    ) -> tuple[str, dict[str, Any]] | None:
        template_entry = _TASK_TEMPLATES.get(task)
        if template_entry is None:
            return None

        cypher, required_entities = template_entry
        parameters: dict[str, Any] = {}

        if task == "eta_lookup":
            order_id = entities.get("order_id")
            if not order_id and entities.get("shipment_id"):
                order_id = entities["shipment_id"]
            if not order_id:
                return None
            parameters["order_id"] = order_id

        elif task == "shipment_lookup":
            shipment_id = entities.get("shipment_id") or entities.get("order_id")
            if not shipment_id or not _is_valid_shipment_reference(shipment_id):
                return None
            parameters["shipment_id"] = shipment_id

        else:
            for key in required_entities:
                value = entities.get(key)
                if not value:
                    return None
                parameters[key] = value

        _validate_read_only(cypher)
        return _normalize_cypher(cypher), parameters

    @staticmethod
    def _from_llm(
        task: str,
        entities: dict[str, str],
        schema: str,
    ) -> tuple[str, dict[str, Any]] | None:
        prompt = f"""
You generate read-only Neo4j Cypher for logistics graph lookups.

{schema}

Task: {task}
Entities: {entities}

Rules:
- Use only the allowed nodes and relationships listed above.
- Use parameters from the entities dictionary.
- Return ONLY Cypher.
- No explanations.
- No markdown.
- No comments.
- Read-only MATCH/RETURN queries only.
""".strip()

        try:
            client = get_client()
            response = client.chat.completions.create(
                model=get_model(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=512,
            )
            cypher = (response.choices[0].message.content or "").strip()
            cypher = re.sub(r"^```(?:cypher)?\s*", "", cypher, flags=re.I)
            cypher = re.sub(r"\s*```$", "", cypher)
            cypher = _normalize_cypher(cypher)
            if not cypher:
                return None
            _validate_read_only(cypher)
            parameters = {
                key: value
                for key, value in entities.items()
                if key != "self_scoped"
            }
            return cypher, parameters
        except Exception:
            logger.exception("LLM Cypher generation failed for task=%s", task)
            return None
