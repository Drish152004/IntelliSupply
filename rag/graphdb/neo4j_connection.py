import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, NotificationMinimumSeverity

_ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_FILE)

# Driver 5.21+ logs DBMS notifications to stderr by default in dev mode.
logging.getLogger("neo4j.notifications").setLevel(logging.CRITICAL)
logging.getLogger("neo4j").setLevel(logging.WARNING)


class Neo4jConnection:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

        missing = [
            name
            for name, value in (
                ("NEO4J_URI", self.uri),
                ("NEO4J_USER", self.user),
                ("NEO4J_PASSWORD", self.password),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"Missing Neo4j environment variables: {', '.join(missing)}. "
                f"Set them in {_ENV_FILE} (see .env.example)."
            )

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            warn_notification_severity=NotificationMinimumSeverity.OFF,
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None):
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(self, query, parameters=None):
        with self.driver.session(database=self.database) as session:
            session.execute_write(
                lambda tx: tx.run(query, parameters or {}).consume()
            )