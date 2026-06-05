from aura_graphdb.aura_connection import AuraConnection


AURA_CONSTRAINTS = [
    """
    CREATE CONSTRAINT aura_profile_id_unique IF NOT EXISTS
    FOR (p:Profile)
    REQUIRE p.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_profile_email_unique IF NOT EXISTS
    FOR (p:Profile)
    REQUIRE p.email IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_role_name_unique IF NOT EXISTS
    FOR (r:Role)
    REQUIRE r.role_name IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_prediction_id_unique IF NOT EXISTS
    FOR (p:Prediction)
    REQUIRE p.prediction_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_route_prediction_id_unique IF NOT EXISTS
    FOR (r:RoutePrediction)
    REQUIRE r.prediction_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_eta_prediction_id_unique IF NOT EXISTS
    FOR (e:ETAPrediction)
    REQUIRE e.prediction_id IS UNIQUE
    """
]


def create_aura_constraints():
    conn = AuraConnection()

    try:
        for query in AURA_CONSTRAINTS:
            print("Running constraint:")
            print(query)
            conn.execute_write(query)

        print("Aura constraints created successfully.")

    finally:
        conn.close()


if __name__ == "__main__":
    create_aura_constraints()