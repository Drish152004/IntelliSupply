# AUTHENTICATION AND RBAC FLOW ANALYSIS

This report details the authentication mechanics, role propagation, authorization layers, and courier workflows in the IntelliSupply platform.

---

## 1. COMPLETE AUTHENTICATION FLOW

### 1.1 Step-by-Step Login Pipeline
When a user logs in via the React frontend:
1. **Frontend Request**: The credentials (email and password) are collected by [Login.tsx](file:///c:/Users/Relanto/Desktop/IntelliSupply/frontend/app/src/pages/Login.tsx) and passed to the `login` function of the `AuthProvider` in [auth.tsx](file:///c:/Users/Relanto/Desktop/IntelliSupply/frontend/app/src/lib/auth.tsx).
2. **API Call**: The client makes a POST request to `/api/login` on the FastAPI backend gateway.
3. **Database Lookups**: The backend `/api/login` endpoint (in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/routers/auth.py)) triggers `_try_login(email, password)`:
   - **Profiles Check**: It checks the PostgreSQL database (via Supabase auth client `get_user_by_email` in [supabase_auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/rag/aura_graphdb/supabase_auth.py)) for a match. If found, it validates the password against the stored bcrypt hash using `bcrypt.checkpw()`.
   - **Couriers Check**: If not in profiles, it checks the Neo4j Aura Graph database (via `login_courier` in [aura_courier.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/rag/aura_graphdb/aura_courier.py)) for a `Courier` node. If found, it validates the password against the stored Werkzeug hash using `check_password_hash()`.
4. **Token Generation**: If valid, the backend creates a signed JWT using `create_access_token` in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/dependencies/auth.py) containing user metadata claims (`sub`, `email`, `name`, `role`, `role_id`, `courier_id`).
5. **Frontend Storage**: The frontend client receives the JWT token and user details, saving them to `localStorage` under keys `intellisupply_token` and `intellisupply_user`.
6. **Token Verification**: Subsequent frontend API calls retrieve the token from `localStorage` and include it in the `Authorization: Bearer <token>` header. The backend validates this token in REST endpoints via the FastAPI dependency `get_current_user`.

### 1.2 Auth Real vs Mocked & Offline Fallback
- **Database/Backend Auth**: **REAL**. Real passwords are hashed and compared (via bcrypt and Werkzeug check). Real JWT tokens are signed using `HS256` and the `JWT_SECRET` key.
- **Frontend Demo Auth**: **MOCKED**. If the backend API cannot be reached and `DEMO_ENABLED` is true, the frontend falls back to offline demo logins (e.g. `admin@demo.com` with password `admin`, defined in [auth.tsx](file:///c:/Users/Relanto/Desktop/IntelliSupply/frontend/app/src/lib/auth.tsx)). This sets fake user properties locally, but generates no token, causing any future backend API requests to fail with a `401 Unauthorized` error.
- **Google OAuth**: **PARTIALLY MOCKED**. Backend endpoints exist to authenticate and callback via Google (defined in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/routers/auth.py)). If successful, a profile is registered in Neo4j (via `login_or_register_google_user`). However, there is no sync with the Supabase Postgres DB, and the React frontend does not implement any UI buttons to trigger Google OAuth.

### 1.3 Key Files, Functions, and Route Handlers

#### Frontend
- **Auth Provider**: `AuthProvider` in [auth.tsx](file:///c:/Users/Relanto/Desktop/IntelliSupply/frontend/app/src/lib/auth.tsx)
- **Token Injection & Fetch**: `apiFetch` in [api.ts](file:///c:/Users/Relanto/Desktop/IntelliSupply/frontend/app/src/lib/api.ts)
- **Route Guard**: `ProtectedRoute` in [ProtectedRoute.tsx](file:///c:/Users/Relanto/Desktop/IntelliSupply/frontend/app/src/components/ProtectedRoute.tsx)

#### Backend
- **Unified Gateway Config**: `configure_auth` in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/routers/auth.py)
- **API Login Handler**: `api_login` in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/routers/auth.py)
- **Token Verification Dependency**: `get_current_user` in [auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/FastAPI/dependencies/auth.py)
- **Database Password Validation**: `login_user_with_password` in [supabase_auth.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/rag/aura_graphdb/supabase_auth.py) and `login_courier` in [aura_courier.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/rag/aura_graphdb/aura_courier.py)

---

## 2. COMPLETE RBAC FLOW

### 2.1 How RBAC Works
IntelliSupply enforces RBAC across two main levels:
1. **API Role Constraints**: Restricted via the FastAPI dependency `require_roles(*roles)`.
2. **Agentic Orchestrator Constraints**: Handled inside the LangGraph pipeline via the `rbac` node (calling `enforce_rbac` in [rbac_node.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/agentic_ai/orchestrator/rbac_node.py)) and resource-level checks via `authorize_courier_resource` (defined in [resource_rbac.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/agentic_ai/orchestrator/resource_rbac.py)).

### 2.2 Permissions Matrix
The platform defines four central user roles (`admin`, `logistics_manager`, `inventory_manager`, `courier`), which map to internal orchestrator permissions:

| Orchestrator Task | Mapped Role Permissions | Protected Backend Endpoints |
| :--- | :--- | :--- |
| `inventory_nlsql` | `ADMIN`, `INVENTORY` | `/inventory/*` |
| `shipment_lookup` | `ADMIN`, `LOGISTICS` | `/orders/shipments` (GET/POST) |
| `courier_lookup` | `ADMIN`, `LOGISTICS` | `/couriers` (POST) |
| `eta_lookup` | `ADMIN`, `LOGISTICS` | `/eta/predict` (POST) |
| `eta_prediction` | `ADMIN`, `LOGISTICS` | `/eta/predict` (POST) |
| `route_lookup` | `ADMIN`, `LOGISTICS`, `COURIER` | `/route/predict/*` (POST) |
| `route_prediction` | `ADMIN`, `LOGISTICS`, `COURIER` | `/route/predict/*` (POST) |
| `next_stop_prediction` | `ADMIN`, `LOGISTICS`, `COURIER` | `/route/predict/*` (POST) |
| `demand_forecast` | `ADMIN`, `LOGISTICS` | `/demand/predict` (POST) |

### 2.3 Privilege Escalation & Security Gaps
1. **State Recovery Session Spoofing**:
   If an orchestrator call does not receive the `authenticated_user` argument, it falls back to `restore_user_role` in [session_context.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/agentic_ai/orchestrator/rbac/session_context.py):
   ```python
   for session in (logistics_session, inventory_session):
       if session and session.get("user_role"):
           return map_to_orchestrator_role(session["user_role"])
   ```
   If a client sends an API request directly to the orchestrator execution endpoints and omits the JWT header but passes a JSON payload containing `"logistics_session": {"user_role": "ADMIN"}`, the orchestrator will restore the user's role as `ADMIN` and allow access to all nodes. (Though the FastAPI copilot gateway requires a JWT, other entrypoints or tests could trigger this if not protected).
2. **Missing Endpoint-level Filtering (Context Drops)**:
   In FastAPI router handlers like `/orders/shipments` and `/route/predict/next-stop`, the user token dependency validates the role, but the code does `del current_user` without mapping the user ID to database queries. Because of this, a courier user is trusted globally at the endpoint level; any courier can predict routes or query next stops for *any* courier ID in the system by passing the targeted ID in the payload.
3. **Cache Bypass of Fine-Grained Authorization**:
   The standard cache lookup runs before the graph retrieval or agent execution nodes. If a query hits the cache (e.g. Courier A's route query cached under a deterministic key), the orchestrator immediately formats the response and skips all future nodes. If Courier B queries the same details, the cached result is returned, bypassing the `GraphAuthorizer.check()` resource-level ownership block.

---

## 3. COURIER FLOW ANALYSIS

The courier workflow is partially implemented but fragmented. While courier database records exist and authentication succeeds, there are significant gaps in UI support, dashboarding, and endpoint-level data isolation.

### 3.1 Courier Data Isolation
- **Orchestrator Level**: Isolated. The `GraphAuthorizer` (in [graph_authorizer.py](file:///c:/Users/Relanto/Desktop/IntelliSupply/agentic_ai/graph_retrieval/graph_authorizer.py)) checks if the role is `COURIER`. If so, it extracts the `courier_id` from the session context (JWT token claims). If the query targets a different courier ID, the graph retrieval is blocked with a denial reason.
- **API Router Level**: Not Isolated. The endpoints in `/orders/` and `/route/` do not perform user ID mapping. If a courier queries `/orders/shipments?limit=100`, they are blocked at the role check level. If they query the ML prediction endpoint directly, they can fetch predictions for any courier.

### 3.2 Key System Gaps for Courier Support

To fully support a production courier flow, the following architectural elements are missing:

1. **Courier-Specific Dashboard Mismatch**:
   Couriers are allowed access to the `/logistics` frontend route, but this page queries `/orders/shipments` to display a list of all hubs and shipments. This API call requires the `logistics_manager` role, meaning the page returns a `403 Forbidden` error for couriers.
2. **Lack of Shipment Ownership Constraints**:
   Order and shipment tables have an `assigned_courier_id` column, but the API router has no filter logic. To support courier isolation, `/orders/shipments` should support a `/orders/shipments/me` or query parameters like `/orders/shipments?courier_id=...` that match the session's validated courier ID.
3. **Interactive Route Completion UI**:
   There is no frontend view for couriers to mark route stops as completed or trigger route rerouting. Although the orchestrator state supports tracking completed stops (`stops_completed`), this value cannot be updated from the UI.
4. **Google Maps / Leaflet Real-Time Location**:
   The `RouteMap` Leaflet visualization reads raw orders lat/lng fields but does not bind to the courier's real-time coordinate state or update their `start_lat_wgs84` / `start_lon_wgs84` properties in Neo4j.
