# Inventory Planning Workspace: Scenario-First Integration

The Inventory Planning Workspace connects the React frontend to the simulation agent via a **scenario-first** workflow. Simulation runs only when the user provides a what-if scenario (typed or via example chips), not from entity scope filters alone.

---

## API Endpoints

### 1. `GET /planning/context`
- **Frontend:** `getPlanningContext()` in [api.ts](frontend/app/src/lib/api.ts)
- **Purpose:** Loads hubs, products, categories, dates, and valid combinations from `demand_forecast_daily.csv` for entity scope dropdowns.

### 2. `POST /planning/understand`
- **Frontend:** `understandPlanningScenario()` in [api.ts](frontend/app/src/lib/api.ts)
- **Backend:** `understand_planning_scenario` in [planning.py](FastAPI/routers/planning.py)
- **Purpose:** Stage 1 — converts natural-language scenario text into a `ScenarioPatch`. Returns `complete` with patch or `needs_clarification` with questions.

### 3. `POST /planning/simulate`
- **Frontend:** `simulatePlanning()` in [api.ts](frontend/app/src/lib/api.ts)
- **Backend:** `simulate_planning` in [planning.py](FastAPI/routers/planning.py)
- **Purpose:** Runs Stages 0–12 when entity scope + scenario (`patch` or `scenario_query`) are provided. Returns full pipeline result plus `scenario_query` and `applied_patch`.

---

## User Flow

1. Select **entity scope** (Hub → Category → Product → Simulation Date)
2. Enter a **what-if scenario** or click an example chip
3. Click **Run Simulation** (disabled until both scope and scenario are set)
4. View **Inventory State**, **Outcome Discovery**, **Intervention Ranking**, and **Explainability** panels

### Example Scenarios (preset patches)

| Chip | Scenario query |
|------|----------------|
| Launch promotion | What would happen over the next 7 days if I launch a promotion? |
| Replenishment delay | What would happen if my incoming replenishment is delayed by 5 days? |
| Demand surge | What would happen if demand increases by 30% over the next week? |
| Epidemic in winter | What would happen if an epidemic occurs during winter? |

Presets apply a resolved `ScenarioPatch` immediately (no LLM call). Custom queries are parsed via `/understand` before simulation.

---

## Frontend Components

Located in `frontend/app/src/components/planning/`:

| Component | Purpose |
|-----------|---------|
| `EntityScopePanel` | Hub / category / product / date selectors |
| `ScenarioInputPanel` | NL textarea, example chips, patch preview, clarification UI |
| `RunSimulationBar` | Gated run button |
| `PlanningIdleState` | Shown before first successful run |
| `InventoryStatePanel` | Scenario state telemetry cards |
| `OutcomeDiscoveryPanel` | Baseline aggregates + best/likely/worst worlds |
| `InterventionRankingPanel` | Ranked corrective decisions |
| `ExplainabilityPanel` | LLM / template explanations |

Types and helpers: [planningTypes.ts](frontend/app/src/lib/planningTypes.ts), examples: [planningExamples.ts](frontend/app/src/lib/planningExamples.ts).

---

## Roles

Planning page and API allow: `admin`, `inventory_manager`, `logistics_manager`.
