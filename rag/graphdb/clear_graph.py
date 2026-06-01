from graphdb.neo4j_connection import neo4j_conn


def clear_graph():
    query = """
    MATCH (n)
    DETACH DELETE n
    """

    neo4j_conn.execute_query(query)
    print("Graph cleared successfully.")


if __name__ == "__main__":
    clear_graph()
    neo4j_conn.close()