# Agentic AI

LangGraph orchestrator with retrieval-only RAG: inventory NL-SQL and logistics Aura GraphDB lookups.

## Entry points

| Command | Purpose |
|---------|---------|
| `python agentic_ai/main.py` | Interactive CLI |
| `POST /copilot/query` | HTTP copilot (via unified FastAPI gateway) |

## Pipeline

```
init_state → rbac_coarse → entity_extraction → intent → entity_resolution
  → parameter_preparation → rag_executor → response_formatter
```

## Layout

| Folder | Role |
|--------|------|
| `orchestrator/` | LangGraph workflow, RBAC, intent, RAG executor, response formatting |
| `orchestrator/task_registry.py` | Domains, tasks, keywords, permissions |
| `integrations/` | SQL bridge, Aura bridge, LLM client, language detection |
| `context/` | Entity extraction, clarification |

## Configuration

Secrets live in the repo root [`.env`](../.env.example). Optional:

- `HF_TOKEN` — for multilingual detection/translation in `init_state`

## Further reading

- [Root README](../README.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
