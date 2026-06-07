# IntelliSupply

**AI-native supply chain intelligence** — unified inventory, demand forecasting, last-mile dispatch, and conversational operations across databases, knowledge graphs, and ML models.

IntelliSupply connects warehouse and hub data with logistics ML (clustering, courier assignment, route sequencing, ETA) and agentic copilots that answer operational questions in plain English. It is built for real dispatch workflows: learned delivery sequences (not only shortest-path routing), leakage-safe models, and optional Neo4j GraphRAG over your network.

---

## Table of contents

- [Capabilities](#capabilities)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Running services](#running-services)
- [Configuration](#configuration)
- [Development workflows](#development-workflows)
- [Testing](#testing)
- [Documentation](#documentation)
- [Roadmap](#roadmap)

---

## Capabilities

| Area | What it does |
|------|----------------|
| **Order clustering** | Groups nearby deliveries (DBSCAN on geospatial features) |
| **Courier assignment** | Maps clusters to couriers via historical assignments or live nearest-available matching |
| **Route sequencing** | LightGBM ranker predicts next stop / full route from courier state (LaDe-trained, v3 honest features) |
| **ETA prediction** | Estimates delivery time in minutes with spatial, temporal, and courier workload features |
| **Demand forecasting** | Regional package demand inference (lags, rolling stats, calendar features) |
| **Inventory Q&A** | Natural language → SQL over Postgres (products, warehouses, hubs) |
| **Logistics GraphRAG** | Neo4j knowledge graph + LLM-generated Cypher (hubs, couriers, orders, routes) |
| **Agentic orchestration** | LangGraph routes queries to inventory or logistics specialist agents |
| **Operator UI** | React dashboard: overview KPIs, inventory, route map + shipment panel + copilot sidebar |

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         Frontend (React + Vite)                          │
│              Overview · Inventory · Logistics map + copilot              │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                    Agentic AI (LangGraph orchestrator)                   │
│         Intent → Router → Inventory agent | Logistics agent              │
│              NL-to-SQL · Demand ML · GraphRAG · ETA · Routes             │
└───────┬─────────────────┬──────────────────────┬────────────────────────┘
        │                 │                      │
        ▼                 ▼                      ▼
┌───────────────┐  ┌──────────────┐    ┌────────────────────────────────┐
│ Postgres      │  │ Neo4j        │    │ ML services                     │
│ (inventory)   │  │ (logistics   │    │ Route ranker · ETA · Demand     │
│               │  │  graph)      │    │ Full pipeline: cluster→assign→  │
└───────────────┘  └──────────────┘    │ sequence → maps (OSRM/AMap)     │
                                       └────────────────────────────────┘
                                                    ▲
                                       ┌────────────┴────────────┐
                                       │ FastAPI unified gateway  │
                                       │  /route · /demand · /eta │
                                       └─────────────────────────┘
```

**Design principle:** the ranker decides *which stop comes next*; the routing engine decides *how to drive between stops*. Agents and APIs share the same inference code paths.

---

## Repository structure

```text
IntelliSupply/
├── config/                    # Shared paths and env loader
├── notebooks/route_prediction/  # Training notebooks (local) + route_ranker.pkl
├── frontend/app/              # React + Vite + Tailwind operator UI
├── FastAPI/                   # Unified ML API gateway (/route, /demand, /eta)
├── agentic_ai/                # LangGraph orchestrator + inventory/logistics agents
├── ml/                        # Orchestrator ML adapter layer
├── ml_services/
│   ├── route_prediction/      # LightGBM ranker, full dispatch pipeline
│   ├── eta-prediction/        # ETA model training & inference
│   └── demand_forecasting/    # Regional demand model + HF space
├── rag/
│   ├── inventory/             # NL-to-SQL chatbot over Postgres
│   └── graphdb/               # Neo4j load + GraphRAG
├── tests/                     # Root pytest suite
└── README.md                  # This file
```

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.12+** | Recommended for agents, RAG, and ML |
| **Node.js 18+** | Frontend (`frontend/app`) |
| **NVIDIA API key** | Agents and GraphRAG use [NVIDIA NIM](https://build.nvidia.com/) (`integrate.api.nvidia.com`) |
| **Postgres** | Inventory NL-to-SQL (Neon / Supabase direct URL) |
| **Neo4j 5.x** (optional) | Logistics GraphRAG; agents fall back to route/ETA ML without it |
| **Supabase** (optional) | One-time load of logistics tables into Neo4j |
| **Trained artifacts** | `route_ranker.pkl`, demand/ETA pickles (see workflows below) |

---

## Quick start

### 1. Clone and Python environment

```powershell
cd C:\Users\Relanto\IntelliSupply
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies per component you need (see [Running services](#running-services)).

### 2. Environment file

Copy the example and fill in secrets (never commit `.env`):

```powershell
copy .env.example .env
# Edit .env with your keys
```

For the frontend, optionally copy `frontend/app/.env.example` to `frontend/app/.env.local`.

See [Configuration](#configuration).

### 3. Start the unified ML API

```powershell
pip install -r FastAPI/requirements.txt
python FastAPI/run.py
```

Open http://127.0.0.1:8000/docs — health, route, demand, and ETA endpoints.

### 4. Start the frontend

```powershell
cd frontend\app
npm install
npm run dev
```

Open the URL Vite prints (typically http://localhost:5173). Default route: `/routes` (logistics map).

### 5. Run the agent CLI (optional)

```powershell
pip install -r agentic_ai/requirements.txt
pip install -r rag/requirements.txt
cd agentic_ai
python main.py
```

---

## Running services

### Unified ML API (`FastAPI/`)

Single gateway for all inference.

```powershell
pip install -r FastAPI/requirements.txt
python FastAPI/run.py
```

| Endpoint prefix | Description |
|-----------------|-------------|
| `GET /health` | Service load status |
| `/route` | Next-stop and full-route sequence prediction |
| `/demand` | Regional demand forecasting |
| `/eta` | Delivery ETA (minutes) |

Details: [FastAPI/README.md](FastAPI/README.md)

**Port conflict (Windows):** if port 8000 is in use, `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F`, or `$env:PORT=8001; python FastAPI/run.py`.

### Frontend (`frontend/app/`)

```powershell
cd frontend\app
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
| Route | Page |
|-------|------|
| `/routes` | Logistics map, shipments, AI copilot sidebar |
| `/inventory` | Stock and warehouse views |
| `/overview` | KPI dashboard + floating copilot |

Build for production: `npm run build` then `npm run preview`.

### Agentic orchestrator (`agentic_ai/`)

Interactive CLI with intent routing and tool-calling agents:

- **Inventory:** `nl_to_sql`, `predict_demand`
- **Logistics:** `graphrag_query`, `predict_eta`, `predict_next_stop`, `predict_route_sequence`

```powershell
pip install -r agentic_ai/requirements.txt
cd agentic_ai
python main.py
```

Agents call ML inference in-process via `agentic_ai/integrations/ml_bridge.py` (same logic as `FastAPI/services/`).

### RAG — inventory chatbot

Requires root `.env` with `DATABASE_URL` and `NVIDIA_API_KEY`.

```powershell
pip install -r rag/requirements.txt
cd rag\inventory
python -m chatbot.chatbot
```

### RAG — Neo4j graph load & GraphRAG

One-time setup (Windows example):

```powershell
pip install -r rag/requirements.txt
cd rag
python -m graphdb.create_constraints
python -m graphdb.load_graph
python -m graphdb.graph_rag
```

Without Neo4j, logistics agent questions still work via **route/ETA ML** (`graph_used: false`).  
Full guide: [rag/graphdb/README.md](rag/graphdb/README.md).

---

## Configuration

All services load a **single** root [`.env`](.env.example) via [`config/env.py`](config/env.py). Copy `.env.example` to `.env` and fill in values.

### NVIDIA / LLM (agents + GraphRAG)

```env
NVIDIA_API_KEY=your_key
GRAPH_LLM_MODEL=meta/llama-3.1-8b-instruct
```

### Inventory Postgres

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname
```

### Neo4j + Supabase (graph load)

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=intellisupply
SUPABASE_DB_HOST=...
SUPABASE_DB_PASSWORD=...
```

See [`.env.example`](.env.example) for the full list (auth, Aura, ML overrides, frontend `VITE_API_URL`).

### Route model path

Default: `notebooks/route_prediction/route_ranker.pkl`.  
Override: `ROUTE_RANKER_MODEL` env var.

---

## Development workflows

### Train the route ranker

1. Place `route_prediction_pipeline.ipynb` under `notebooks/route_prediction/` (notebooks are gitignored).
2. Run from `notebooks/route_prediction/` so `Couriers_seg/Delivery.csv` resolves.
3. Pass sanity checks (`READY_FOR_FULL_TRAIN`) before full-dataset training.
4. Export `route_ranker.pkl` to `notebooks/route_prediction/`.

Metrics, leakage fixes, and feature list: [ml_services/route_prediction/README.md](ml_services/route_prediction/README.md).

### Run the full dispatch pipeline (demo)

End-to-end: **cluster → courier assign → sequence predict → JSON/CSV/map outputs**.

```powershell
# From repo root (requires route_ranker.pkl + cluster_assignments.csv from notebook outputs)
python -m ml_services.route_prediction.full_pipeline.run_demo
```

| Input | Path |
|-------|------|
| Sample orders | `ml_services/route_prediction/full_pipeline/data/synthetic_orders.json` |
| Sample couriers | `ml_services/route_prediction/full_pipeline/data/synthetic_couriers.json` |
| Outputs | `ml_services/route_prediction/full_pipeline/outputs/` |

Pipeline code: `ml_services/route_prediction/full_pipeline/pipeline.py`.

### Phase-1 clustering notebook

`notebooks/route_prediction/phase1_clustering.ipynb` — produces `cluster_assignments.csv` in `notebooks/route_prediction/outputs/` used by `CourierAssigner`.

---

## Testing

Install dev dependencies and run the full suite from repo root:

```powershell
pip install -r FastAPI/requirements.txt -r agentic_ai/requirements.txt -r requirements-dev.txt
pytest -v
```

### Orchestrator (legacy CLI runner)

```powershell
cd agentic_ai
python -m tests.test_orchestrator
```

---

## Documentation

| Topic | Location |
|-------|----------|
| Route prediction, metrics, inference API | [ml_services/route_prediction/README.md](ml_services/route_prediction/README.md) |
| Unified ML gateway | [FastAPI/README.md](FastAPI/README.md) |
| Demand forecasting | [ml_services/demand_forecasting/README.md](ml_services/demand_forecasting/README.md) |
| ETA prediction | [ml_services/eta-prediction/README.md](ml_services/eta-prediction/README.md) |
| Neo4j + GraphRAG setup | [rag/graphdb/README.md](rag/graphdb/README.md) |
| Frontend app | [frontend/app/README.md](frontend/app/README.md) |

---

## Roadmap

| Item | Status |
|------|--------|
| Congestion-aware routing & dynamic reassignment | Planned (Phase 3) |
| Planning agent (business problem → phased ops plan) | Planned |
| Deeper frontend ↔ live agent/API integration | In progress |

---

## Security notes

- Do **not** commit `.env`, API keys, or credentials.
- `full_pipeline/outputs/` and HTML route maps are generated artifacts — safe to gitignore for clean repos.
- Rotate keys if they were ever committed.

---

## License

No license file is specified in the repository root. Add one before public distribution.
