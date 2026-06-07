# Agentic AI

LangGraph orchestrator with inventory and logistics specialist agents, RBAC, caching, and graph retrieval.

## Entry points

| Command | Purpose |
|---------|---------|
| `python agentic_ai/main.py` | Interactive CLI |
| `POST /copilot/query` | HTTP copilot (via unified FastAPI gateway) |

## Layout

| Folder | Role |
|--------|------|
| `orchestrator/` | Intent routing, LangGraph workflow, ML node, response formatting |
| `agents/` | Inventory and logistics agent loops with tool calling |
| `integrations/` | Bridges to SQL, GraphRAG, ML inference, LLM client |
| `context/` | Query completeness, entity extraction, payload building |
| `graph_retrieval/` | GraphRAG node, Cypher generation, authorization |
| `cache/` | Session and prediction caching |
| `tests/` | Agentic-specific pytest suite |

## Configuration

All secrets live in the repo root [`.env`](../.env.example) (loaded via [`config/env.py`](../config/env.py)).

## Further reading

- [Root README](../README.md) — quick start and service matrix
- [ARCHITECTURE.md](../ARCHITECTURE.md) — system-wide data flow
