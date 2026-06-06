from aura_graphdb.aura_connection import AuraConnection


AURA_CONSTRAINTS = [
    """
    CREATE CONSTRAINT aura_city_id_unique IF NOT EXISTS
    FOR (c:City)
    REQUIRE c.city_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_hub_id_unique IF NOT EXISTS
    FOR (h:Hub)
    REQUIRE h.hub_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_courier_id_unique IF NOT EXISTS
    FOR (c:Courier)
    REQUIRE c.courier_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_order_id_unique IF NOT EXISTS
    FOR (o:Order)
    REQUIRE o.order_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_notes_id_unique IF NOT EXISTS
    FOR (n:Notes)
    REQUIRE n.notes_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_route_prediction_id_unique IF NOT EXISTS
    FOR (r:RoutePrediction)
    REQUIRE r.route_prediction_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_hub_name_unique IF NOT EXISTS
    FOR (h:Hub)
    REQUIRE h.name IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_courier_id_unique IF NOT EXISTS
    FOR (c:Courier)
    REQUIRE c.courier_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_courier_email_unique IF NOT EXISTS
    FOR (c:Courier)
    REQUIRE c.email IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_role_id_unique IF NOT EXISTS
    FOR (r:Role)
    REQUIRE r.role_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_role_name_unique IF NOT EXISTS
    FOR (r:Role)
    REQUIRE r.role_name IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_route_prediction_id_unique IF NOT EXISTS
    FOR (r:RoutePrediction)
    REQUIRE r.route_prediction_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_eta_prediction_id_unique IF NOT EXISTS
    FOR (e:ETAPrediction)
    REQUIRE e.eta_prediction_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_order_id_unique IF NOT EXISTS
    FOR (o:Order)
    REQUIRE o.order_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT aura_notes_id_unique IF NOT EXISTS
    FOR (n:Notes)
    REQUIRE n.notes_id IS UNIQUE
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