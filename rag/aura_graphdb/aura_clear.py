from aura_graphdb.aura_connection import AuraConnection


def clear_aura_graph():
    conn = AuraConnection()

    query = """
    MATCH (n)
    DETACH DELETE n
    """

    try:
        conn.execute_write(query)
        print("Aura graph cleared successfully.")

    finally:
        conn.close()


if __name__ == "__main__":
    clear_aura_graph()