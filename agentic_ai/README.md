# Agentic AI

LangGraph orchestrator with retrieval-only RAG: inventory NL-SQL and logistics Aura GraphDB lookups.

## Entry points

| Command | Purpose |
|---------|---------|
| `python agentic_ai/main.py` | Interactive CLI |
| `POST /copilot/query` | HTTP copilot (via unified FastAPI gateway) |

## Pipeline

```
init_state → rbac_coarse → semantic_cache → intent → rbac_fine → param_resolver → rag_executor → format
```

## Layout

| Folder | Role |
|--------|------|
| `orchestrator/` | LangGraph workflow, RBAC, intent, RAG executor, response formatting |
| `orchestrator/task_registry.py` | Domains, tasks, keywords, permissions, cache TTL |
| `integrations/` | SQL bridge, Aura bridge, LLM client, language detection |
| `context/` | Entity extraction, query completeness, clarification |
| `cache/` | Semantic similarity cache |

## Configuration

Secrets live in the repo root [`.env`](../.env.example). Optional:

- `SEMANTIC_CACHE_ENABLED` — default `true`
- `SEMANTIC_CACHE_THRESHOLD` — cosine similarity threshold (default `0.88`)
- `HF_TOKEN` — for multilingual detection/translation in `init_state`

## Further reading

- [Root README](../README.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
