from pathlib import Path
from graphdb.neo4j_connection import Neo4jConnection

def run_constraints():
    conn = Neo4jConnection()

    constraint_file = Path("graphdb/cypher/constraints.cypher")

    if not constraint_file.exists():
        constraint_file = Path("cypher/constraints.cypher")

    cypher_text = constraint_file.read_text(encoding="utf-8")

    statements = [
        stmt.strip()
        for stmt in cypher_text.split(";")
        if stmt.strip()
    ]

    for stmt in statements:
        print(f"Running:\n{stmt}\n")
        conn.execute_write(stmt)

    conn.close()
    print("Constraints created successfully.")


if __name__ == "__main__":
    run_constraints()