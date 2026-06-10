# PRODUCTION SECURITY AUDIT

This document evaluates the security posture of the IntelliSupply enterprise AI logistics platform. It identifies vulnerabilities, insecure design patterns, and critical production readiness gaps across the platform's layers.

---

## 1. AUTHENTICATION & SESSION VULNERABILITIES

### 1.1 Insecure Local Storage of JWTs & User Data
- **Vulnerability**: The React frontend (in [auth.tsx](file:///c:/Users/Relanto/Desktop/IntelliSupply/frontend/app/src/lib/auth.tsx)) stores the access token (`intellisupply_token`) and user properties (`intellisupply_user`) directly in browser `localStorage`.
- **Impact**: `localStorage` is accessible to any script running on the same domain. If an Cross-Site Scripting (XSS) vulnerability exists anywhere in the frontend or third-party packages, an attacker can extract these credentials and hijack user sessions.
- **Remediation**: Transition to storing JWTs in HTTP-only, secure, `SameSite=Strict` cookies.

### 1.2 Lack of Refresh Tokens & Excessive JWT Lifetimes
- **Vulnerability**: The access tokens are configured with a hardcoded, excessively long expiration time (`1440` minutes, i.e., 24 hours, in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/dependencies/auth.py)). There is no refresh token implementation.
- **Impact**: Stolen access tokens can be used by an attacker for 24 hours without interruption. There is no backend blacklist or logout endpoint to revoke active tokens immediately; logout simply deletes local client storage.
- **Remediation**: Reduce access token lifetime to 15 minutes, implement short-lived refresh tokens stored in HTTP-only cookies, and implement token rotation and blacklist tracking.

### 1.3 Cryptographic Inconsistencies in Password Hashing
- **Vulnerability**: User profiles are stored in Supabase PostgreSQL and verified via `bcrypt` (defined in [supabase_auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/rag/aura_graphdb/supabase_auth.py)), while Courier users are stored in Neo4j and verified via Werkzeug's `check_password_hash` (defined in [aura_courier.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/rag/aura_graphdb/aura_courier.py)).
- **Impact**: Code base complexity increases, and future database migrations are prone to hash mismatch bugs. Werkzeug's default PBKDF2 hash is also less secure against GPU-based offline brute-force attacks than bcrypt.
- **Remediation**: Standardize hashing on `bcrypt` or `argon2id` across all user database backends.

### 1.4 Missing CSRF Protection & Insecure Starlette Sessions
- **Vulnerability**: FastAPI uses Starlette `SessionMiddleware` signed with `FASTAPI_SECRET_KEY` (configured in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/routers/auth.py)). The key falls back to a default `"dev-secret-change-this"`. No CSRF validation token is sent or checked on form submissions in the legacy endpoints.
- **Impact**: Vulnerable to session hijacking if the default key is committed to production, and vulnerable to Cross-Site Request Forgery (CSRF) on session-based endpoints.
- **Remediation**: Require strong session keys in production and implement CSRF tokens for form-based requests.

---

## 2. RBAC & PRIVILEGE ESCALATION VULNERABILITIES

### 2.1 State Recovery Session Spoofing
- **Vulnerability**: The orchestrator's state recovery method `restore_user_role` (in [session_context.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/agentic_ai/orchestrator/rbac/session_context.py)) reads the user's role directly from client-supplied sessions if the `authenticated_user` argument is omitted:
  ```python
  for session in (logistics_session, inventory_session):
      if session and session.get("user_role"):
          return map_to_orchestrator_role(session["user_role"])
  ```
- **Impact**: If an API route or another entrypoint invokes the orchestrator and fails to forward user claims, an attacker can escalate their privileges to `ADMIN` by appending `"user_role": "admin"` to their payload session.
- **Remediation**: The orchestrator must never trust roles sent inside client sessions. Roles must always be verified against the backend JWT context.

### 2.2 Missing Endpoint-Level Resource Ownership Checks
- **Vulnerability**: Multiple FastAPI routes (like `/orders/shipments` and `/route/predict/*`) validate user roles but delete the user object context (`del current_user`) before database execution.
- **Impact**: Any user with the role can retrieve or alter data belonging to other users. For example, a courier can fetch routes or next-stop sequence predictions for any courier ID in the platform by altering parameters in the POST body.
- **Remediation**: Map the verified user's identity claims directly to database queries. Implement filter scopes like `WHERE c.email = $authenticated_email`.

### 2.3 Cache Authentication Bypass
- **Vulnerability**: The query cache node (`cache_lookup` in [cache_node.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/agentic_ai/orchestrator/cache_node.py)) runs before graph retrieval and execution. If there is a cache hit, the orchestrator returns the cached data immediately.
- **Impact**: Cache keys are generated solely from task and query entities. If Courier A queries a shipment and the result is cached, Courier B (who should be blocked by fine-grained resource rules) will get a cache hit and view the details, bypassing the GraphAuthorizer checks.
- **Remediation**: Include the user's ID, role, or authorized scope as part of the cache key structure (e.g. `key = f"user_id:task:hash"`).

---

## 3. AI, LLM, AND QUERY VULNERABILITIES

### 3.1 Weak Cypher Generator Validation (Bypasses)
- **Vulnerability**: The Cypher validation check in [graph_rag.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/rag/graphdb/graph_rag.py) uses a blocklist matching exact strings:
  ```python
  blocked = ["CREATE ", "MERGE ", "DELETE ", ...]
  ```
- **Impact**: An attacker can bypass this check using space variations (e.g. `CREATE(n)` or `merge(c)` without spaces) or by injecting Cypher statements inside comments. Since the validator only checks if the query starts with MATCH/WITH/OPTIONAL MATCH, nested write commands or transaction controls are executable.
- **Remediation**: Use an abstract syntax tree (AST) parser to validate that Neo4j Cypher queries are strictly read-only.

### 3.2 SQL Injection on Natural Language to SQL
- **Vulnerability**: The NL-to-SQL bridge (in [sql_bridge.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/agentic_ai/integrations/sql_bridge.py)) executes LLM-generated SQL statements directly using SQLAlchemy:
  ```python
  result = conn.execute(text(generated_sql))
  ```
  The only validation is `generated_sql.strip().lower().startswith("select")`.
- **Impact**: An attacker can use prompt injection (e.g. "show iphones; drop table products;") to execute arbitrary SQL statements. Since the application starts with a SELECT statement, the check passes.
- **Remediation**: Run database connections using read-only database users with restricted schema tables (e.g., block the connection from access to `profiles`, `roles`, and administrative schemas).

---

## 4. MACHINE LEARNING INFERENCE GAPS

### 4.1 Unsafe Pickle Loading
- **Vulnerability**: Both LightGBM models (ETA and Route sequencing) are loaded using Python's `pickle.load` or `_RoutePredictorUnpickler.load` (defined in [route_predictor.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/ml_services/route_prediction/route_predictor.py) and [inference.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/ml_services/eta-prediction/full_pipeline/inference.py)).
- **Impact**: `pickle` is highly vulnerable to arbitrary code execution. If an attacker can replace model files in the file system or intercept the model registry path, they can execute shell commands inside the application environment.
- **Remediation**: Export and load ML models using secure formats like ONNX, PMML, or LightGBM's native `save_model`/`Booster(model_file=...)` serialization API.

### 4.2 Repeated Model Reload Gaps
- **Vulnerability**: The `adapt_eta_payload` dynamically calls wrappers which import packages during runtime. If not structured correctly, models could be repeatedly loaded into memory, causing high memory usage and response latency.
- **Remediation**: Standardize model warm-up at startup and lazy-load using strict singletons in `registry.py`.

---

## 5. INFRASTRUCTURE & DEPLOYMENT GAPS

### 5.1 Permissive CORS Configurations
- The main FastAPI app uses `allow_origins=["*"]`, allowing any domain to send API queries. In production, this must be restricted to specific domain lists.

### 5.2 Default Environment Fallbacks
- Secret variables like `FASTAPI_SECRET_KEY` and `JWT_SECRET` fall back to insecure default strings. This can lead to security breaches if the environment file is not populated correctly.

### 5.3 Missing Observability & Tracing
- The platform lacks unified logging, request tracing, and exception handling. In the event of an exploit, auditing or reconstructing the attack vector is difficult due to missing request log structures.
- **Remediation**: Integrate open telemetry tracing, structured JSON logging, and error tracking tools.
