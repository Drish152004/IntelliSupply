"""Dynamic read-only Cypher generation and execution for Neo4j Aura.

This file converts a natural-language logistics question into a Cypher query
using an NVIDIA-hosted LLM, validates that the query is read-only, executes it
against AuraDB, and returns the result rows.

Environment variables required:
- NVIDIA_API_KEY
- GRAPH_LLM_MODEL, optional default: meta/llama-3.1-8b-instruct
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

from config.env import load_env
from rag.aura_graphdb.aura_connection import AuraConnection

load_env()

logger = logging.getLogger(__name__)

GRAPH_LLM_MODEL = os.getenv("GRAPH_LLM_MODEL", "meta/llama-3.1-8b-instruct")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

if not NVIDIA_API_KEY:
    raise RuntimeError(
        "NVIDIA_API_KEY is not loaded. Check .env and config.paths.ENV_FILE."
    )

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
)
AURA_GRAPH_SCHEMA = """
You generate safe read-only Neo4j Cypher for an AuraDB logistics graph.

====================
NODE SCHEMA
====================

City:
- city_id
- city_name

Hub:
- hub_id
- name
- hub_name
- city_id
- city_name
- lat
- lng
- hub_type
- representative_aoi_id
- representative_typecode
- created_at
- updated_at

Courier:
- courier_id: internal long hex id, example "7f1fb69bd86cf657201ef76c26de9ace"
- name: human name, examples "Courier 1", "Courier 9", "Courier 10"
- email
- profile_id
- hub_id
- hub_name: courier base/start hub name
- city_id
- city_name
- start_lat_wgs84
- start_lon_wgs84
- is_active
- ds
- created_at
- updated_at

Order:
- order_id
- assigned_courier_id: internal Courier.courier_id value
- from_hub_name
- to_hub_name
- city_name
- delivery_day: string date like "2026-06-03"
- receipt_time
- route_sequence
- lat_wgs84
- lon_wgs84
- receipt_lat_wgs84
- receipt_lon_wgs84
- typecode
- aoi_id
- nearest_courier_distance_m
- notes_text
- ds
- created_at
- updated_at

RoutePrediction:
- route_prediction_id
- courier_id
- order_ids
- predicted_sequence
- predicted_eta_min
- predicted_stops_json
- stops_json
- delivery_day
- city_name
- ds
- stop_count
- route_start_time
- created_at
- updated_at

Profile:
- id
- name
- email
- auth_provider
- source
- is_active
- created_at
- updated_at

Role:
- role_id
- role_name
- created_at
- updated_at

Notes:
- notes_id
- text
- courier_id
- created_at
- updated_at

====================
RELATIONSHIP SCHEMA
====================

(:Hub)-[:LOCATED_IN]->(:City)

(:Hub)-[:CONNECTED_TO]->(:Hub)
CONNECTED_TO properties:
- raw_distance_km
- map_distance_km
- estimated_time_min
- city_id

(:Courier)-[:ASSIGNED_TO_HUB]->(:Hub)
Meaning: courier base/start hub only. Not order source/destination hub.

(:Courier)-[:OPERATES_IN]->(:City)
(:Courier)-[:HAS_ROLE]->(:Role)
(:Courier)-[:LINKED_TO_PROFILE]->(:Profile)

(:Profile)-[:HAS_ROLE]->(:Role)

(:Order)-[:ASSIGNED_TO]->(:Courier)
Meaning: order is assigned to courier.
Important: direction is Order -> Courier.

(:Order)-[:FROM_HUB]->(:Hub)
Meaning: order pickup/source/from hub.

(:Order)-[:TO_HUB]->(:Hub)
Meaning: order destination/to hub.

(:Order)-[:BELONGS_TO_CITY]->(:City)
(:Order)-[:HAS_NOTES]->(:Notes)

(:RoutePrediction)-[:FOR_COURIER]->(:Courier)
(:RoutePrediction)-[:BELONGS_TO_CITY]->(:City)

(:RoutePrediction)-[:HAS_STOP]->(:Order)
HAS_STOP properties:
- sequence
- lat_wgs84
- lon_wgs84

====================
INTENT INTERPRETATION RULES
====================

Before generating Cypher:

STEP 1:
Determine which business entity the question is PRIMARILY about.
Possible primary entities:
- Order
- Courier
- RoutePrediction
- Hub
- City

STEP 2:
Generate Cypher anchored on that primary entity.
Never choose an Order pattern simply because Order nodes exist in the graph.
The presence of orders is not a reason to use Order-[:ASSIGNED_TO]->Courier.

ROUTE INTERPRETATION RULES:
If the user asks about any of:
- route, routes, assigned routes, courier routes, route plan,
- route prediction, predicted route, delivery route,
- route sequence, stop sequence
then the primary entity is RoutePrediction.
Use RoutePrediction relationships first:
  MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier)
Do NOT default to:
  MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)
unless the user EXPLICITLY asks about orders.
A "route assigned to a courier" is a RoutePrediction, NOT a list of assigned orders.

ORDER INTERPRETATION RULES:
Use Order only when the question is explicitly about:
- orders, deliveries, packages, assigned orders, order counts,
- order lookup, order destinations, order hubs
Only then use:
  MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)

HUB INTERPRETATION RULES:
If the user asks about:
- route between hubs, connected hubs, path between hubs, travel between hubs
then prefer:
  (:Hub)-[:CONNECTED_TO]->(:Hub)
Do not use Order relationships for hub-connectivity questions.

ENTITY PRIORITY (when multiple entities could match):
- RoutePrediction > Order  (when the question is about routes)
- Hub connectivity > Order  (when the question is about hub-to-hub paths)
- Courier route > assigned orders  (when the question is about a courier's route)

Worked examples:
- "What routes have been assigned to each courier?" -> primary entity RoutePrediction, NOT Order.
- "What orders are assigned to each courier?" -> primary entity Order.

====================
IMPORTANT INTERPRETATION RULES
====================

Courier:
- If user says "Courier 9", use c.name = "Courier 9".
- Do not use c.courier_id = 9.
- Use c.courier_id only if user says courier_id or gives a long internal hex id.

Hub:
- For display, use coalesce(h.name, h.hub_name).
- If user says "Hub 12", match coalesce(h.name, h.hub_name) = "Hub 12".
- Use h.hub_id only if user explicitly says hub_id.

Order assignment:
- Correct pattern is:
  MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)
- Never use:
  (c:Courier)-[:ASSIGNED_TO]->(o:Order)

Courier base hub:
- Use (:Courier)-[:ASSIGNED_TO_HUB]->(:Hub) only for courier base/start/assigned hub.

Order hubs:
- Use (:Order)-[:FROM_HUB]->(:Hub) and (:Order)-[:TO_HUB]->(:Hub) for order source/destination hubs.
- Do not use ASSIGNED_TO_HUB for order hub questions.

Status/completion:
- Order does not have status, completed_at, delivered_at, in_transit, cancelled, or actual_delivery_time.
- Do not infer completed deliveries from receipt_time.
- If user asks for completed deliveries, use assigned orders as fallback and alias as assigned_order_count.
- If user asks for in-transit orders, list assigned orders only.

ETA/time:
- Order does not have actual delivery duration.
- For ETA or average delivery time, use RoutePrediction.predicted_eta_min.
- Alias clearly as predicted ETA, for example average_predicted_eta_min.
- For last 30 days/month, use:
  date(x.delivery_day) >= date() - duration({days: 30})
- Never use date() - 30.

Cypher scope:
- After WITH, only variables included in WITH are available.
- If using:
  WITH c, count(DISTINCT o) AS assigned_order_count
  then do not use o later.

====================
QUERY RULES
====================

- Generate only one Cypher query.
- Read-only queries only.
- Never use CREATE, MERGE, DELETE, DETACH, SET, REMOVE, DROP, LOAD CSV, CALL, APOC, or FOREACH.
- No explanations.
- No markdown fences.
- Return only fields directly requested by the user.
- Do not add email, profile_id, is_active, timestamps, ds, city_name, or coordinates unless asked.
- Use clear aliases with AS.
- Add LIMIT for list queries.
- Do not add LIMIT for pure aggregation/count queries.
- For counts, always use clear aliases:
  count(DISTINCT c) AS city_count
  count(DISTINCT c) AS courier_count
  count(DISTINCT o) AS order_count
- When listing a single courier's ORDERS, order by o.route_sequence when available.
  This applies only to order listings; it does NOT mean "route" questions use Order.
- For courier ROUTE questions, use RoutePrediction (see INTENT INTERPRETATION RULES),
  and use rp.predicted_sequence / rp.stop_count rather than Order.route_sequence.
- For RoutePrediction stops, order by HAS_STOP.sequence.

====================
FEW-SHOT EXAMPLES
====================

User question:
how many cities are there?

Cypher:
MATCH (c:City)
RETURN count(DISTINCT c) AS city_count

User question:
How many couriers are there in the system?

Cypher:
MATCH (c:Courier)
RETURN count(DISTINCT c) AS courier_count

User question:
What is the total number of orders in the system?

Cypher:
MATCH (o:Order)
RETURN count(DISTINCT o) AS order_count

User question:
List all orders assigned to courier 9

Cypher:
MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)
WHERE c.name = "Courier 9"
RETURN
    c.name AS courier_name,
    o.order_id AS order_id
ORDER BY o.route_sequence, o.order_id
LIMIT 50

User question:
show couriers and their base hubs

Cypher:
MATCH (c:Courier)-[:ASSIGNED_TO_HUB]->(h:Hub)
RETURN DISTINCT
    c.name AS courier_name,
    coalesce(h.name, h.hub_name) AS courier_base_hub
ORDER BY courier_name
LIMIT 50

User question:
show couriers and their order hubs

Cypher:
MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)
OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)
RETURN
    c.name AS courier_name,
    o.order_id AS order_id,
    coalesce(fromHub.name, fromHub.hub_name, o.from_hub_name) AS from_hub,
    coalesce(toHub.name, toHub.hub_name, o.to_hub_name) AS to_hub
ORDER BY courier_name, o.route_sequence, o.order_id
LIMIT 50

User question:
List all couriers who have completed more than 5 deliveries.

Cypher:
MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)
WITH c, count(DISTINCT o) AS assigned_order_count
WHERE assigned_order_count > 5
RETURN
    c.name AS courier_name,
    assigned_order_count
ORDER BY assigned_order_count DESC

User question:
What is the average delivery time for orders in the last month?

Cypher:
MATCH (rp:RoutePrediction)
WHERE date(rp.delivery_day) >= date() - duration({days: 30})
RETURN
    avg(toFloat(rp.predicted_eta_min)) AS average_predicted_eta_min

User question:
List all orders that are currently in transit.

Cypher:
MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)
RETURN
    o.order_id AS order_id,
    c.name AS courier_name
ORDER BY o.route_sequence, o.order_id
LIMIT 50

User question:
List all couriers who have more than 5 deliveries.

Cypher:
MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier)
WITH c, count(DISTINCT o) AS assigned_order_count
WHERE assigned_order_count > 5
RETURN
    c.name AS courier_name,
    assigned_order_count
ORDER BY assigned_order_count DESC

User question:
show route prediction for Courier 4 on 2026-06-03

Cypher:
MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier)
WHERE c.name = "Courier 4"
  AND rp.delivery_day = "2026-06-03"
RETURN
    c.name AS courier_name,
    rp.route_prediction_id AS route_prediction_id,
    rp.predicted_sequence AS predicted_sequence,
    rp.predicted_eta_min AS predicted_eta_min,
    rp.stop_count AS stop_count
LIMIT 50

User question:
what routes have been assigned to each courier

Cypher:
MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier)
RETURN
    c.name AS courier_name,
    rp.predicted_sequence AS route_sequence,
    rp.stop_count AS stop_count,
    rp.predicted_eta_min AS predicted_eta_min
ORDER BY courier_name
LIMIT 50

User question:
show all courier routes

Cypher:
MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier)
RETURN
    c.name AS courier_name,
    rp.predicted_sequence AS route_sequence,
    rp.delivery_day AS delivery_day,
    rp.stop_count AS stop_count
ORDER BY courier_name
LIMIT 50

User question:
which couriers have active routes

Cypher:
MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier)
RETURN
    c.name AS courier_name,
    rp.delivery_day AS delivery_day,
    rp.stop_count AS stop_count
ORDER BY courier_name
LIMIT 50

User question:
show routes for Courier 4

Cypher:
MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier)
WHERE c.name = "Courier 4"
RETURN
    c.name AS courier_name,
    rp.predicted_sequence AS route_sequence,
    rp.predicted_eta_min AS predicted_eta_min,
    rp.stop_count AS stop_count
LIMIT 50

User question:
show route assignments by courier

Cypher:
MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier)
RETURN
    c.name AS courier_name,
    rp.route_prediction_id AS route_id,
    rp.stop_count AS stop_count
ORDER BY courier_name
LIMIT 50

User question:
show the route between Hub 2 and Hub 5

Cypher:
MATCH (fromHub:Hub)-[r:CONNECTED_TO]->(toHub:Hub)
WHERE coalesce(fromHub.name, fromHub.hub_name) = "Hub 2"
  AND coalesce(toHub.name, toHub.hub_name) = "Hub 5"
RETURN
    coalesce(fromHub.name, fromHub.hub_name) AS from_hub,
    coalesce(toHub.name, toHub.hub_name) AS to_hub,
    r.map_distance_km AS map_distance_km,
    r.estimated_time_min AS estimated_time_min
LIMIT 50
"""
READ_ONLY_ALLOWED_STARTS = (
    "MATCH",
    "OPTIONAL MATCH",
    "WITH",
)

BLOCKED_CYPHER_KEYWORDS = {
    "CREATE",
    "MERGE",
    "DELETE",
    "DETACH",
    "SET",
    "REMOVE",
    "DROP",
    "LOAD",
    "FOREACH",
    "CALL",
    "APOC",
    "CREATE INDEX",
    "CREATE CONSTRAINT",
    "DROP INDEX",
    "DROP CONSTRAINT",
}

def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences if the LLM returns ```cypher ... ```."""
    text = text.strip()

    fence_match = re.search(
        r"```(?:cypher|sql)?\s*(.*?)```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fence_match:
        return fence_match.group(1).strip()

    return text


def _extract_cypher_from_response(content: str) -> str:
    """Extract Cypher from LLM response.

    The prompt asks for only Cypher, but this makes it robust if the model
    returns JSON or fenced code.
    """
    content = content.strip()

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and parsed.get("cypher"):
            return str(parsed["cypher"]).strip()
    except json.JSONDecodeError:
        pass

    cypher = _strip_markdown_fences(content)

    # Remove common prefixes if model ignores instructions.
    cypher = re.sub(r"^\s*cypher\s*:\s*", "", cypher, flags=re.IGNORECASE)
    cypher = cypher.strip().rstrip(";").strip()

    return cypher


def _ensure_limit(cypher: str, default_limit: int = 50) -> str:
    """Add a LIMIT if the generated query has no LIMIT and is not pure aggregation."""
    if re.search(r"\bLIMIT\b", cypher, flags=re.IGNORECASE):
        return cypher

    upper = cypher.upper()

    aggregation_patterns = (
        r"\bCOUNT\s*\(",
        r"\bAVG\s*\(",
        r"\bSUM\s*\(",
        r"\bMIN\s*\(",
        r"\bMAX\s*\(",
    )

    if any(re.search(pattern, upper) for pattern in aggregation_patterns):
        return cypher

    return f"{cypher}\nLIMIT {int(default_limit)}"

def validate_read_only_cypher(cypher: str) -> None:
    """Raise ValueError if generated Cypher is unsafe or not read-only."""
    if not cypher or not cypher.strip():
        raise ValueError("Generated Cypher is empty.")

    cleaned = cypher.strip().rstrip(";").strip()
    upper = re.sub(r"\s+", " ", cleaned.upper())

    if not upper.startswith(READ_ONLY_ALLOWED_STARTS):
        raise ValueError(
            "Only read-only Cypher starting with MATCH, OPTIONAL MATCH, or WITH is allowed."
        )

    # Block dangerous keywords.
    # Keep this strict because the query is generated by an LLM.
    for keyword in BLOCKED_CYPHER_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, upper):
            raise ValueError(f"Unsafe Cypher keyword blocked: {keyword}")

    if ";" in cleaned:
        raise ValueError("Multiple Cypher statements are not allowed.")

def _json_safe(value: Any) -> Any:
    """Convert Neo4j values into JSON-safe Python values."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}

    if hasattr(value, "iso_format"):
        return value.iso_format()

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def _rows_to_dicts(rows: Any) -> list[dict[str, Any]]:
    """Convert Neo4j result rows into plain dictionaries."""
    output: list[dict[str, Any]] = []

    for row in rows or []:
        row_dict = dict(row)
        output.append({key: _json_safe(value) for key, value in row_dict.items()})

    return output


def _scope_instruction(scope: dict[str, Any] | None) -> str:
    """Build a mandatory courier scope block injected into the generation prompt.

    Returns an empty string when there is no courier scope (ADMIN / LOGISTICS).
    This is one defense layer only: the orchestrator's authorize node guarantees
    the scope, and run_dynamic_cypher post-filters rows as the authoritative guard.
    """
    if not scope:
        return ""
    courier_id = str((scope or {}).get("courier_id") or "").strip()
    if not courier_id:
        return ""
    return f"""
====================
MANDATORY SECURITY SCOPE
====================

You may ONLY return data belonging to the courier whose courier_id = "{courier_id}".
Whenever the query touches Courier, Order, or RoutePrediction, you MUST filter to this courier:
- Courier: WHERE c.courier_id = "{courier_id}"
- Order assignment: MATCH (o:Order)-[:ASSIGNED_TO]->(c:Courier) WHERE c.courier_id = "{courier_id}"
- RoutePrediction: MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(c:Courier) WHERE c.courier_id = "{courier_id}"
Never return data for any other courier. Never aggregate across couriers.
""".strip()


def _apply_scope_filter(
    rows: list[dict[str, Any]],
    scope: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Authoritative defense-in-depth: drop rows referencing another courier_id.

    Rows that carry a ``courier_id``-like column whose value differs from the
    bound courier are removed. Rows without any courier identifier are retained
    (the prompt scope already constrained them).
    """
    if not scope:
        return rows
    courier_id = str((scope or {}).get("courier_id") or "").strip()
    if not courier_id:
        return rows

    filtered: list[dict[str, Any]] = []
    for row in rows:
        mismatched = False
        for key, value in row.items():
            if "courier_id" in str(key).lower():
                cell = str(value).strip()
                if cell and cell != courier_id:
                    mismatched = True
                    break
        if not mismatched:
            filtered.append(row)
    return filtered


def generate_dynamic_cypher(
    question: str,
    *,
    default_limit: int = 50,
    scope: dict[str, Any] | None = None,
) -> str:
    """Generate a read-only Cypher query from a natural-language question.

    When ``scope`` carries a courier_id, a mandatory scope block is injected so
    the generated Cypher is constrained to that courier's data.
    """
    if not os.getenv("NVIDIA_API_KEY"):
        raise ValueError("NVIDIA_API_KEY is not set.")

    scope_block = _scope_instruction(scope)

    prompt = f"""
{AURA_GRAPH_SCHEMA}
{scope_block}

User question:
{question}

Generate only the Cypher query.
""".strip()

    response = client.chat.completions.create(
        model=GRAPH_LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Neo4j Cypher generator for a logistics AuraDB graph. "
                    "First resolve the user's intent: decide the PRIMARY business "
                    "entity (Order, Courier, RoutePrediction, Hub, or City) per the "
                    "INTENT INTERPRETATION RULES, then anchor the query on it. "
                    "Route questions use RoutePrediction, not Order assignments. "
                    "Return only one safe read-only Cypher query. "
                    "Do not explain. Do not use markdown. "
                    "Follow the schema and few-shot examples exactly."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.0,
        max_tokens=700,
    )

    content = response.choices[0].message.content or ""
    cypher = _extract_cypher_from_response(content)
    cypher = _ensure_limit(cypher, default_limit=default_limit)

    validate_read_only_cypher(cypher)

    return cypher


def run_dynamic_cypher(
    question: str,
    *,
    default_limit: int = 50,
    scope: dict[str, Any] | None = None,
    entities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate Cypher from a question, execute it on Aura, and return rows.

    ``scope`` (e.g. {"courier_id": ...}) restricts results to a single courier:
    it is injected into the generation prompt and enforced again by an
    authoritative post-execution row filter. ``entities`` is accepted for future
    canonical-id hints; it is currently unused by generation.
    """
    conn = AuraConnection()

    try:
        cypher = generate_dynamic_cypher(question, default_limit=default_limit, scope=scope)
        rows = conn.execute_query(cypher)
        result_rows = _apply_scope_filter(_rows_to_dicts(rows), scope)

        return {
            "success": True,
            "question": question,
            "cypher": cypher,
            "count": len(result_rows),
            "rows": result_rows,
        }

    except Exception as exc:
        logger.exception("Dynamic Cypher failed")

        return {
            "success": False,
            "question": question,
            "cypher": None,
            "count": 0,
            "rows": [],
            "message": str(exc),
        }

    finally:
        conn.close()
        
def get_dynamic_cypher_rows(
    question: str,
    *,
    default_limit: int = 50,
) -> list[dict[str, Any]]:
    """Return only result rows for callers that do not need Cypher/debug metadata."""
    result = run_dynamic_cypher(question, default_limit=default_limit)

    if not result.get("success"):
        return []

    return result.get("rows", [])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    question = input("Ask AuraDB: ").strip()
    result = run_dynamic_cypher(question)

    print(json.dumps(result, indent=2, ensure_ascii=False))