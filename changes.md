# Inventory Planning Workspace: UI Integration & Bug Fixes

This document outlines the API endpoints, UI integration flow, and all bug fixes and refactoring completed on the **Inventory Planning Workspace** page.

---

## 1. UI & Endpoint Integration Mapping

The Inventory Planning Workspace connects the React frontend to the FastAPI planning and simulation pipeline via two endpoints.

### API Endpoints
1.  **Fixtures Endpoint (`GET /planning/fixtures`)**
    *   **Frontend Call**: `getPlanningFixtures()` in [api.ts](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/frontend/app/src/lib/api.ts)
    *   **Backend Handler**: `get_planning_fixtures` in [planning.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/planning.py)
    *   **Purpose**: Extracts all unique hubs, products, categories, and dates from `demand_forecast_daily.csv` alongside the list of valid `combinations` to dynamically populate dropdown lists on load.

2.  **Simulation Run Endpoint (`POST /planning/run`)**
    *   **Frontend Call**: `runPlanningSimulation(payload)` in [api.ts](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/frontend/app/src/lib/api.ts)
    *   **Backend Handler**: `run_planning_simulation` in [planning.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/planning.py)
    *   **Purpose**: Runs the full planning pipeline (Stages 0–12), executing Monte Carlo simulations and Discrete Event Simulations (DES) to return scenarios, outcomes, and ranked corrective decisions.

### Frontend Component Layout

*   **`TopFilters`**: Renders dropdown selects for Hub, Category, Product, Date, and Planning Window, along with the "Run Simulation" trigger button.
*   **`StateCards`**: Renders a telemetry grid (Inventory, Demand, Risk, Event, Replenishment) populated from `simulationData.scenario`.
*   **`CaseScenarioCards`**: Exposes Best Case, Most Likely, and Worst Case scenarios for comparative logging.
*   **`DecisionCards`**: Lists recommended mitigations (e.g., expedite PO, transfer stock) sorted by benefit score.
*   **Modals**: 
    *   `StateCardDetailsModal` (telemetry inspection).
    *   `ScenarioModal` (daily log timeline details).
    *   `DecisionModal` (explanation and comparison of simulated decision benefit metrics).

---

## 2. Completed Bug Fixes & Refactoring

Here is the log of issues identified and fixed to secure the planning application state:

### 1. Filter Validation Fix
*   **Issue**: Standard filters didn't check for category-hub-product availability constraints, occasionally triggering 500 errors when submitting out-of-sync parameters to pandas query functions.
*   **Fix**: Modified the available choices memo filters to filter products strictly matching the selected category and hub, and hubs strictly matching category and product.

### 2. Hierarchical Dependency Refactoring
*   **Issue**: Mutually dependent filters created circular reactive pathways, causing select options to reset randomly and trigger cascading updates.
*   **Fix**: Replaced circular logic with a strict unidirectional hierarchy:
    $$\text{Hub} \rightarrow \text{Category} \rightarrow \text{Product} \rightarrow \text{Date}$$
    *   Hubs are derived directly from the full fixtures options list.
    *   Categories list filters strictly by selected Hub.
    *   Products list filters strictly by selected Hub + Category.
    *   Dates list filters strictly by selected Hub + Category + Product combination.

### 3. State Initialization Safety
*   **Issue**: Dropdowns initialized to hardcoded values (e.g. `hubFilter = '0'`, `productFilter = 'P0008'`), which might not exist in the CSV configurations for some roles or datasets.
*   **Fix**: Initialized filters to empty strings (`""`). Cascading alignment effects trigger sequentially to select the first valid combination once the fixtures dataset is fetched.

### 4. Explicit Triggering ("Run Simulation" Button)
*   **Issue**: Changing filters triggered `runPlanningSimulation` automatically on every keystroke, causing severe backend CPU load, request bottlenecks, and UI layout jumps.
*   **Fix**: Restricted execution to manual trigger click. Added a **"Run Simulation"** button that sets a state flag (`runRequested = true`). The fetch effect only runs when the flag is true, clearing it inside a `finally` block once resolved. The button is disabled when filter combinations are unaligned or loading.

### 5. Race Condition Protection (Request ID Tracking)
*   **Issue**: Changing filters and triggering multiple simulation requests sequentially caused out-of-order responses, where slow stale responses overwrote new data.
*   **Fix**: Implemented request tracking inside `Planning.tsx` via `requestIdRef = useRef(0)`. We capture a local `currentRequestId` per run and discard the returned payload if it doesn't match the current request ID (`currentRequestId === requestIdRef.current`), resolving race conditions.
