import os
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config.env import load_env
from openai import OpenAI

from graphdb.neo4j_connection import Neo4jConnection  # noqa: F401 — legacy local dev

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
You are working with a Neo4j logistics graph (Aura).

Node labels and properties:

City:
- city_id
- city_name

Hub:
- hub_id
- name
- latitude
- longitude
- city_name

Courier:
- courier_id
- name
- email
- city_name
- hub_id
- hub_name
- ds
- is_active

Order:
- order_id
- from_hub_name
- to_hub_name
- city_name
- delivery_day
- receipt_time
- assigned_courier_id
- lat_wgs84
- lon_wgs84

RoutePrediction:
- route_prediction_id
- courier_id
- city_name
- delivery_day
- predicted_sequence

Relationships:

(:Hub)-[:LOCATED_IN]->(:City)
(:Courier)-[:OPERATES_IN]->(:City)
(:Courier)-[:ASSIGNED_TO_HUB]->(:Hub)
(:Order)-[:FROM_HUB]->(:Hub)
(:Order)-[:TO_HUB]->(:Hub)
(:Order)-[:ASSIGNED_TO]->(:Courier)
(:Order)-[:BELONGS_TO_CITY]->(:City)
(:RoutePrediction)-[:FOR_COURIER]->(:Courier)

Important:
- Hub names look like Hub_1, Hub_12 (match on h.name).
- Orders do NOT have shipment_id; use order_id only.
- For counts between hubs, match Order nodes with from_hub_name and to_hub_name.
- Use LIMIT 20 unless the query is a count or aggregation.
- Return only valid Cypher.
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
9. For shipment/order questions, use Order nodes and FROM_HUB / TO_HUB:
   MATCH (o:Order)-[:FROM_HUB]->(fromHub:Hub)
   MATCH (o:Order)-[:TO_HUB]->(toHub:Hub)
10. For counts between two hubs, filter on from_hub_name / to_hub_name or hub names:
   MATCH (o:Order) WHERE o.from_hub_name = 'Hub_1' AND o.to_hub_name = 'Hub_2' RETURN count(o) AS shipment_count
11. Do not reference shipment_id (property does not exist).
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

def run_cypher(cypher: str, parameters=None):
    rag_path = str(_REPO_ROOT / "rag")
    if rag_path not in sys.path:
        sys.path.insert(0, rag_path)

    from aura_graphdb.aura_connection import AuraConnection

    conn = AuraConnection()
    try:
        return conn.execute_query(cypher, parameters or {})
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