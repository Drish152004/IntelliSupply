import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config.env import load_env
from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import Neo4jError, ServiceUnavailable

_env_loaded = False
_CONNECTION_TIMEOUT_SEC = 10


def _load_aura_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    load_env()
    _env_loaded = True


def _use_local_neo4j() -> bool:
    return os.getenv("NEO4J_USE_LOCAL", "").strip().lower() in ("1", "true", "yes")


def _resolve_config() -> tuple[str, str, str, str, str]:
    """Return uri, user, password, database, backend label."""
    _load_aura_env()

    if _use_local_neo4j():
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        backend = "local Neo4j"
        missing = [
            name
            for name, value in (
                ("NEO4J_URI", uri),
                ("NEO4J_USER", user),
                ("NEO4J_PASSWORD", password),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"NEO4J_USE_LOCAL is enabled but missing: {', '.join(missing)}. "
                "Set them in the repo root .env (see .env.example) and start Neo4j on localhost:7687."
            )
        return uri, user, password, database, backend

    uri = os.getenv("NEO4J_AURA_URI")
    user = os.getenv("NEO4J_AURA_USER")
    password = os.getenv("NEO4J_AURA_PASSWORD")
    database = os.getenv("NEO4J_AURA_DATABASE")
    backend = "Neo4j Aura"

    if not uri:
        raise ValueError(
            "Missing NEO4J_AURA_URI. Set Aura credentials in the repo root .env, "
            "or set NEO4J_USE_LOCAL=true to use local Neo4j (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)."
        )
    if not user:
        raise ValueError("Missing NEO4J_AURA_USER")
    if not password:
        raise ValueError("Missing NEO4J_AURA_PASSWORD")
    if not database:
        raise ValueError("Missing NEO4J_AURA_DATABASE")

    return uri, user, password, database, backend


def _hostname_from_uri(uri: str) -> str | None:
    parsed = urlparse(uri.replace("neo4j+ssc://", "https://").replace("neo4j+s://", "https://").replace("bolt://", "http://"))
    return parsed.hostname


def _preflight_dns(uri: str) -> None:
    host = _hostname_from_uri(uri)
    if not host or host in ("localhost", "127.0.0.1"):
        return
    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ConnectionError(
            f"Cannot resolve Neo4j host '{host}'. The Aura instance may be paused, deleted, "
            f"or the URI in the repo root .env is outdated. "
            f"Get a fresh URI from https://console.neo4j.io/ or set NEO4J_USE_LOCAL=true "
            f"and run local Neo4j on bolt://localhost:7687. ({exc})"
        ) from exc


def _format_neo4j_error(exc: Exception, backend: str) -> str:
    message = str(exc)
    if "getaddrinfo failed" in message or "Failed to DNS resolve" in message:
        return (
            f"{backend} is unreachable (DNS lookup failed). "
            "Update NEO4J_AURA_URI in the repo root .env from the Neo4j Aura console, "
            "or set NEO4J_USE_LOCAL=true and start local Neo4j."
        )
    if "Connection refused" in message:
        return (
            f"{backend} refused the connection. "
            "If using local Neo4j, start the database (Docker Desktop or Neo4j Desktop). "
            "If using Aura, confirm the instance is running."
        )
    return f"{backend} error: {message}"


_graph_query_observer = None


def register_graph_query_observer(observer):
    """Register an optional callback invoked before each graph query executes."""
    global _graph_query_observer
    _graph_query_observer = observer


class AuraConnection:
    def __init__(self):
        self.uri, self.user, self.password, self.database, self._backend = _resolve_config()
        _preflight_dns(self.uri)

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=basic_auth(self.user, self.password),
            connection_timeout=_CONNECTION_TIMEOUT_SEC,
        )

        try:
            self.driver.verify_connectivity()
        except (ServiceUnavailable, Neo4jError, OSError) as exc:
            self.driver.close()
            raise ConnectionError(_format_neo4j_error(exc, self._backend)) from exc

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None):
        if _graph_query_observer is not None:
            try:
                _graph_query_observer(query, parameters or {})
            except Exception:
                pass
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except (ServiceUnavailable, Neo4jError, OSError) as exc:
            raise ConnectionError(_format_neo4j_error(exc, self._backend)) from exc

    def execute_write(self, query, parameters=None):
        try:
            with self.driver.session(database=self.database) as session:
                return session.execute_write(
                    lambda tx: [record.data() for record in tx.run(query, parameters or {})]
                )
        except (ServiceUnavailable, Neo4jError, OSError) as exc:
            raise ConnectionError(_format_neo4j_error(exc, self._backend)) from exc
