import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, basic_auth

load_dotenv()


class AuraConnection:
    def __init__(self):
        self.uri = os.getenv("NEO4J_AURA_URI")
        self.user = os.getenv("NEO4J_AURA_USER")
        self.password = os.getenv("NEO4J_AURA_PASSWORD")
        self.database = os.getenv("NEO4J_AURA_DATABASE")

        if not self.uri:
            raise ValueError("Missing NEO4J_AURA_URI")
        if not self.user:
            raise ValueError("Missing NEO4J_AURA_USERNAME")
        if not self.password:
            raise ValueError("Missing NEO4J_AURA_PASSWORD")
        if not self.database:
            raise ValueError("Missing NEO4J_AURA_DATABASE")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=basic_auth(self.user, self.password)
        )

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None):
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(self, query, parameters=None):
        with self.driver.session(database=self.database) as session:
            return session.execute_write(
                lambda tx: [record.data() for record in tx.run(query, parameters or {})]
            )