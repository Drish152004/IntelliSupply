# Agentic AI

This folder contains the IntelliSupply orchestrator for inventory and logistics queries.
It runs a LangGraph state machine that routes user requests through coarse domain detection, authorization, inventory NL-SQL, or logistics GraphDB retrieval.

## High-level flow

1. `agentic_ai/main.py` starts the interactive CLI. It can also be invoked through the unified FastAPI gateway.
2. `orchestrator/graph.py` builds the workflow graph and exposes `run_orchestrator()`.
3. A user query enters the graph as `user_query` and is transformed into an `AgentState`.
4. The graph executes the following main path:

   - `init_state` — set up user, session, and request metadata.
   - `clarification_router` — resume any in-progress HITL (human-in-the-loop) clarification turn.
   - `semantic_cache_lookup` — check role-scoped semantic cache before doing any work.
   - `coarse_authorization` — keyword-based domain detection, domain clarification, and domain-level RBAC.
   - Domain split:
     - `inventory_nlsql` — inventory queries bypass the logistics pipeline and execute raw NL-SQL.
     - `entity_extraction` → `intent` → `entity_resolution` → `authorize` → `parameter_preparation` → `rag_executor` — logistics queries use entity extraction, intent classification, parameter assembly, and Aura GraphDB retrieval.
   - `response_formatter` — build the final normalized JSON response.
   - `semantic_cache_store` — cache successful results.

## Fallback mechanisms

### 1. Semantic cache fallback

- `orchestrator/semantic_cache_lookup_node.py` checks a query-specific semantic cache.
- If Redis is unavailable or errors occur, the cache layer fails open and the system continues normally.
- A cache hit short-circuits directly to `response_formatter`.
- `orchestrator/semantic_cache_store_node.py` only stores successful, authorized, non-clarification responses.
- Cache writes also fail open.

### 2. Domain clarification

- `orchestrator/rbac_coarse.py` performs keyword-based domain detection for `inventory` vs `logistics`.
- Ambiguous queries trigger domain clarification and pause the pipeline until the user answers.
- If a role is not allowed to access a detected domain, the request returns an access denial.

### 3. Intent clarification and task fallback

- Logistics queries proceed to `orchestrator/intent.py` and `orchestrator/intent_task_classifier.py`.
- Low-confidence task classification may trigger clarification instead of executing the wrong task.
- If the classifier determines the query is out of scope for all deterministic logistics tasks and the user role is permitted, it routes the request to the dynamic GraphDB fallback task `dynamic_graph_query`.
- `orchestrator/task_registry.py` defines the deterministic logistics tasks and the dynamic fallback path.

### 4. Graph answer fallback

- `orchestrator/response_formatter.py` uses `orchestrator.answer_generation.py` to produce a natural-language answer from GraphDB results.
- If the answer model fails, returns invalid output, or produces an empty response, it falls back to the rule-based synthesizer in `orchestrator/response_synthesis.py`.
- This ensures a user-visible answer is still produced when the LLM answer layer cannot be trusted.

### 5. Error and authorization handling

- Execution, authorization, and access failures are normalized in `orchestrator/response_formatter.py`.
- The CLI prints these states clearly, while the API gets a structured JSON payload with `status`, `stage`, and `message`.

## Folder and file summary

### Root files

- `main.py` — CLI entry point and interactive loop. It uses `run_orchestrator()` and handles clarification responses.
- `logging_config.py` — basic logging setup for the agent.

### `orchestrator/`

- `graph.py` — constructs the LangGraph workflow and defines routing logic between nodes.
- `init_node.py` — builds initial `AgentState`, loads environment, and sets up user/session metadata.
- `clarification_router_node.py` — resumes clarification turns and routes HITL state.
- `semantic_cache_lookup_node.py` — role-scoped semantic cache lookup node.
- `coarse_authorization.py` — keyword-based domain detection and domain-level RBAC.
- `entity_extraction_node.py` — extracts entities from logistics queries.
- `intent.py` — logistics intent classification and clarification resumption logic.
- `intent_task_classifier.py` — task classification prompt, dynamic fallback detection, and keyword fallback support.
- `entity_resolution_node.py` — resolves entity values and normalizes extracted entities.
- `authorize_node.py` — task-level authorization checks after intent.
- `parameter_preparation_node.py` — assembles parameters for the GraphDB query.
- `rag_executor.py` — executes inventory NL-SQL or logistics Aura GraphDB retrieval.
- `response_formatter.py` — normalizes final state into a consistent JSON response.
- `answer_generation.py` — LLM answer layer for graph results.
- `response_synthesis.py` — deterministic fallback answer synthesis.
- `result_normalizer.py` — converts raw GraphDB output into normalized data for answering.
- `semantic_cache_store_node.py` — writes successful responses back into cache.
- `state.py` — typed agent state definition.
- `task_registry.py` — tasks, domain rules, keyword matching, confidence thresholds, and role permissions.
- `tracing.py` — trace wrappers for graph nodes and observability context.
- `rbac/` — resource-level RBAC helpers, role mapping, and identity validation.
- `resource_rbac.py` — resource-scoped access control for courier/self-scoped data.
- `hitl_session.py` — build/attach/restore clarification sessions and track HITL state.

### `integrations/`

- `aura_bridge.py` — Aura GraphDB connector and function execution layer.
- `sql_bridge.py` — inventory NL-SQL execution layer.
- `llm_client.py` — LLM client setup and model resolution.
- `language.py` — optional language utilities and translation support.

### `context/`

- `entity_extractor.py` — core entity extraction logic used by the logistics pipeline.
- `clarification_manager.py` — clarification prompts and question templates.
- `self_scoped.py` — helper for courier self-scoped authorization.

### `cache/`

- `semantic_cache.py` — higher-level cache abstraction for query/result caching.
- `cache_service.py` — Redis-safe get/set operations that fail open.
- `redis_client.py` — Redis connection wrapper and health check.
- `cache_key.py` — cache key generation.
- `ttl_config.py` — TTL configuration for cache entries.

### `observability/`

- `node_payloads.py` — node payload normalization for telemetry.
- `prompt_capture.py` — prompt logging.
- `redaction.py` — sensitive data redaction utilities.
- `state_metrics.py` — state/performance metrics.
- `trace_events.py` — trace event formatting.

## Notes

- Inventory queries are handled separately via `inventory_nlsql` and do not go through the logistics intent or entity resolution path.
- Dynamic GraphDB fallback is only available for roles in `DYNAMIC_ALLOWED_ROLES` and is intended for queries that no deterministic logistics task can fully answer.
- The system is designed to keep caches and query execution as fail-open as possible so that transient infrastructure issues do not block request processing.

## Related docs

- [Root README](../README.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
