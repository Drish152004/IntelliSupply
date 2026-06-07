import os
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config.env import load_env
from openai import OpenAI

from graphdb.neo4j_connection import Neo4jConnection

load_env()


# =========================================================
# LLM CONFIG
# =========================================================

client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1"
)

MODEL_NAME = os.getenv("GRAPH_LLM_MODEL", "meta/llama-3.1-8b-instruct")


# =========================================================
# GRAPH SCHEMA FOR LLM
# =========================================================

GRAPH_SCHEMA = """
You are working with a Neo4j logistics graph.

Node labels and properties:

City:
- city_id
- city_name

Courier:
- courier_id
- status

Hub:
- hub_id
- name
- poi_lat
- poi_lng
- latitude
- longitude
- aoi_id
- typecode
- rep_dipan_id
- is_warehouse
- is_delivery_hub
- is_mixed_hub
- capacity

HubMetrics:
- hub_id
- pickup_count
- delivery_count
- total
- pickup_ratio
- delivery_ratio

GridRoute:
- grid_route_id
- from_grid_x
- from_grid_y
- to_grid_x
- to_grid_y
- avg_time_sec
- avg_distance_km
- avg_speed_kmph
- num_trips

PickupOrder:
- pickup_id
- from_dipan_id
- accept_time
- book_start_time
- expect_got_time
- poi_lng
- poi_lat
- aoi_id
- typecode
- got_time
- got_gps_time
- got_gps_lng
- got_gps_lat
- ds

DeliveryOrder:
- delivery_id
- from_dipan_id
- poi_lng
- poi_lat
- aoi_id
- typecode
- receipt_time
- receipt_lng
- receipt_lat
- sign_time
- ds

CourierSegment:
- segment_id
- prev_lat
- prev_lng
- lat
- lng
- distance_m
- distance_km
- time_sec
- time_hr
- speed_kmph

Relationships:

(:Courier)-[:OPERATES_IN]->(:City)
(:Hub)-[:LOCATED_IN]->(:City)
(:Hub)-[:HAS_METRICS]->(:HubMetrics)

(:Hub)-[:ROUTE_TO {
    route_id,
    avg_time_min,
    avg_distance_km,
    num_trips
}]->(:Hub)

(:PickupOrder)-[:ASSIGNED_TO]->(:Courier)
(:PickupOrder)-[:BELONGS_TO_CITY]->(:City)

(:DeliveryOrder)-[:ASSIGNED_TO]->(:Courier)
(:DeliveryOrder)-[:BELONGS_TO_CITY]->(:City)

(:Courier)-[:TRAVELLED_SEGMENT]->(:CourierSegment)
(:CourierSegment)-[:USED_GRID_ROUTE]->(:GridRoute)

Important:
- DeliveryOrder may not be loaded yet.
- PickupOrder is currently partially loaded.
- Use LIMIT for large result queries.
- Return only valid Cypher.
- Do not explain the Cypher.
- Do not use SQL.
"""


# =========================================================
# CYPHER GENERATION
# =========================================================

def generate_cypher(user_question: str) -> str:
    prompt = f"""
Given the Neo4j graph schema below, write a Cypher query to answer the user question.

Schema:
{GRAPH_SCHEMA}

User question:
{user_question}

Rules:
1. Return only Cypher.
2. Do not include markdown.
3. Do not include explanation.
4. Use LIMIT 20 unless the query is a count or aggregation.
5. Do not create, update, or delete data.
6. Only use MATCH, OPTIONAL MATCH, WHERE, RETURN, ORDER BY, LIMIT, WITH.
7. Every variable used in RETURN must be defined in MATCH or WITH.
8. For hub-city questions, use:
   MATCH (h:Hub)-[:LOCATED_IN]->(c:City)
9. For hub metrics questions, use:
   MATCH (h:Hub)-[:HAS_METRICS]->(m:HubMetrics)
10. For pickup-courier questions, use:
   MATCH (p:PickupOrder)-[:ASSIGNED_TO]->(c:Courier)
11. For pickup-city questions, use:
   MATCH (p:PickupOrder)-[:BELONGS_TO_CITY]->(city:City)
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are an expert Neo4j Cypher generator for logistics GraphRAG."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0,
        max_tokens=600
    )

    cypher = response.choices[0].message.content.strip()

    cypher = cypher.replace("```cypher", "").replace("```", "").strip()

    return cypher


# =========================================================
# SAFETY CHECK
# =========================================================

def validate_cypher(cypher: str):
    blocked = [
        "CREATE ",
        "MERGE ",
        "DELETE ",
        "DETACH ",
        "SET ",
        "REMOVE ",
        "DROP ",
        "CALL dbms",
        "CALL apoc",
        "LOAD CSV"
    ]

    upper_cypher = cypher.upper()

    for keyword in blocked:
        if keyword.upper() in upper_cypher:
            raise ValueError(f"Unsafe Cypher blocked: {keyword}")

    if not upper_cypher.startswith(("MATCH", "OPTIONAL MATCH", "WITH")):
        raise ValueError("Only read-only Cypher queries are allowed.")


# =========================================================
# RUN CYPHER
# =========================================================

def run_cypher(cypher: str):
    conn = Neo4jConnection()

    try:
        result = conn.execute_query(cypher)
        return result
    finally:
        conn.close()


# =========================================================
# ANSWER GENERATION
# =========================================================

def generate_answer(user_question: str, cypher: str, graph_result):
    result_text = json.dumps(graph_result, indent=2, default=str)

    prompt = f"""
User question:
{user_question}

Cypher query used:
{cypher}

Graph result:
{result_text}

Write a clear answer for the user.

Rules:
- If the result is empty, say that no matching data was found.
- Mention if the data may be partial.
- Do not invent values.
- Keep the answer concise.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You answer logistics questions using Neo4j graph query results."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=700
    )

    return response.choices[0].message.content.strip()


# =========================================================
# MAIN GRAPH RAG FUNCTION
# =========================================================

def ask_graph(user_question: str):
    cypher = generate_cypher(user_question)
    validate_cypher(cypher)

    graph_result = run_cypher(cypher)

    answer = generate_answer(
        user_question=user_question,
        cypher=cypher,
        graph_result=graph_result
    )

    return {
        "question": user_question,
        "cypher": cypher,
        "result": graph_result,
        "answer": answer
    }


# =========================================================
# CLI MODE
# =========================================================

if __name__ == "__main__":
    print("Logistics GraphRAG is ready.")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("Ask logistics graph question: ")

        if question.lower() in ["exit", "quit"]:
            break

        try:
            response = ask_graph(question)

            print("\nGenerated Cypher:")
            print(response["cypher"])

            print("\nAnswer:")
            print(response["answer"])
            print("\n" + "-" * 80 + "\n")

        except Exception as e:
            print(f"Error: {e}")