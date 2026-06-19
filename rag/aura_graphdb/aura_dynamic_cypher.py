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
- For route/order sequence, order by o.route_sequence when available.
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


def generate_dynamic_cypher(
    question: str,
    *,
    default_limit: int = 50,
) -> str:
    """Generate a read-only Cypher query from a natural-language question."""
    if not os.getenv("NVIDIA_API_KEY"):
        raise ValueError("NVIDIA_API_KEY is not set.")

    prompt = f"""
{AURA_GRAPH_SCHEMA}

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
) -> dict[str, Any]:
    """Generate Cypher from a question, execute it on Aura, and return rows."""
    conn = AuraConnection()

    try:
        cypher = generate_dynamic_cypher(question, default_limit=default_limit)
        rows = conn.execute_query(cypher)
        result_rows = _rows_to_dicts(rows)

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