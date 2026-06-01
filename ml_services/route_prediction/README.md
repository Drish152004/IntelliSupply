# IntelliSupply AI — Route Prediction & Courier Dispatch Pipeline

## Table of contents

1. [Project objective & architecture](#project-objective)
2. [Problem definition & LaDe dataset](#1-problem-definition)
3. [Core components (clustering → visualization)](#4-core-components)
4. [Implementation phases](#5-recommended-implementation-phases)
5. [Phase 2 — notebook, v3 pipeline, metrics, inference API](#phase-2--ai-route-prediction)
6. [Phase 3–4 & tech stack](#phase-3--operational-intelligence)
7. [Folder structure & model pipeline](#7-recommended-folder-structure)
8. [Why this project is strong](#9-why-this-project-is-strong)

---

## Project Objective

The goal of the system is to build an AI-powered logistics intelligence platform that can:

1. Automatically cluster delivery orders.
2. Assign optimal couriers to grouped deliveries.
3. Predict the best delivery sequence for each courier.
4. Display intelligent route maps on a courier dashboard.
5. Minimize operational delivery cost and delivery delays.

The system is designed using the LaDe (Last-mile Delivery) dataset and combines:

* machine learning
* graph-based routing
* operational optimization
* courier behavior modeling
* spatial intelligence

This is NOT a simple shortest-path routing system.
It is an AI-assisted delivery operations management platform.

---

# 1. Problem Definition

The project focuses on solving four major logistics problems:

| Problem                                  | Solution                         |
| ---------------------------------------- | -------------------------------- |
| Which orders should be grouped together? | Spatial clustering               |
| Which courier should handle a group?     | Courier assignment optimization  |
| In what order should deliveries happen?  | Route prediction / sequencing    |
| What route should be displayed?          | Route generation + visualization |

---

# 2. Why LaDe Dataset Fits This Problem

The LaDe dataset contains:

* courier trajectories
* delivery timestamps
* package coordinates
* courier IDs
* regions and AOIs
* delivery sequences

This allows the system to learn:

* how real couriers move
* realistic delivery patterns
* congestion behavior
* operational routing decisions

The dataset is ideal for:

* courier dispatch systems
* route sequencing
* operational logistics intelligence

---

# 3. Final System Architecture

The complete pipeline:

```text id="jlwm0"
Incoming Orders
        ↓
Order Clustering
        ↓
Courier Assignment
        ↓
Delivery Sequence Prediction
        ↓
Route Optimization
        ↓
Route Map Generation
        ↓
Courier Dashboard
```

---

# 4. Core Components

---

# Component 1 — Incoming Orders

The system receives delivery requests.

Example input:

```json id="jlwm1"
[
  {
    "order_id": "O101",
    "lat": 12.9716,
    "lng": 77.5946,
    "deadline": "18:00",
    "region": "R12"
  }
]
```

Each order contains:

* location
* region
* timing information
* order metadata

---

# Component 2 — Order Clustering

## Objective

Group geographically nearby deliveries together.

This minimizes:

* travel distance
* fuel cost
* courier workload imbalance

---

# Why clustering is needed

Instead of assigning:

```text id="jlwm2"
1 courier → 1 order
```

the system groups:

```text id="jlwm3"
1 courier → cluster of nearby deliveries
```

This mimics real-world logistics systems.

---

# Recommended Algorithm

## MVP:

### DBSCAN

Why:

* works well with geospatial data
* automatically handles varying delivery densities
* does not require fixed cluster count

---

# Features Used for Clustering

| Feature            | Purpose                  |
| ------------------ | ------------------------ |
| latitude/longitude | geographic proximity     |
| region_id          | regional grouping        |
| aoi_type           | delivery zone similarity |
| delivery deadlines | time-sensitive grouping  |

---

# Example

Orders:

| Order | Region     |
| ----- | ---------- |
| A     | Downtown   |
| B     | Downtown   |
| C     | Downtown   |
| D     | Far suburb |

Output:

```text id="jlwm4"
Cluster 1 → A,B,C
Cluster 2 → D
```

---

# Component 3 — Courier Assignment

## Objective

Assign the most suitable courier to each delivery cluster.

---

# Assignment Logic

The system considers:

* courier current location
* courier availability
* workload
* region familiarity
* estimated route cost

---

# Recommended MVP

## Nearest Available Courier

Assign:

```text id="jlwm5"
closest free courier
```

---

# Advanced Version

Use:

* Hungarian Algorithm
* OR-Tools Assignment Solver

Objective:

```text id="jlwm6"
minimize global delivery cost
```

---

# Features Used for Courier Assignment

| Feature                     | Purpose        |
| --------------------------- | -------------- |
| courier current coordinates | proximity      |
| current workload            | balancing      |
| idle time                   | utilization    |
| assigned region             | specialization |
| estimated completion time   | efficiency     |

---

# Component 4 — Delivery Sequence Prediction

## MOST IMPORTANT COMPONENT

This directly aligns with the original LaDe route prediction task.

---

# Objective

For a courier with multiple assigned deliveries:

```text id="jlwm7"
Predict which delivery should happen next.
```

---

# Example

Assigned deliveries:

```text id="jlwm8"
A, B, C, D
```

Model predicts:

```text id="jlwm9"
A → C → B → D
```

---

# Problem Type

This is:

* ranking
* sequential prediction

NOT shortest path optimization alone.

---

# Why This Matters

Real couriers do not always choose:

* shortest distance
* mathematically optimal route

They are influenced by:

* traffic
* local knowledge
* operational heuristics
* congestion
* delivery density

The model learns realistic delivery behavior.

---

# Recommended Model

## LightGBM Ranker

Recommended because:

* fast training
* interpretable
* strong LaDe benchmark performance
* easier than GNNs

---

# Model Formulation

At each step:

Input:

```text id="jlwm10"
current courier state + candidate stops
```

Output:

```text id="jlwm11"
probability candidate is next stop
```

---

# Training Data Construction

Suppose historical route:

```text id="jlwm12"
Warehouse → A → B → C
```

Training samples:

| Current Stop | Candidate | Label |
| ------------ | --------- | ----- |
| A            | B         | 1     |
| A            | C         | 0     |
| B            | C         | 1     |

---

# Features for Route Prediction

## Spatial Features

| Feature               | Purpose          |
| --------------------- | ---------------- |
| distance_to_candidate | proximity        |
| region transition     | spatial movement |
| AOI type              | area behavior    |
| geohash similarity    | local grouping   |

---

## Temporal Features

| Feature            | Purpose               |
| ------------------ | --------------------- |
| hour of day        | traffic patterns      |
| weekday/weekend    | operational variation |
| elapsed route time | courier fatigue/load  |
| delivery urgency   | prioritization        |

---

## Courier State Features

| Feature              | Purpose           |
| -------------------- | ----------------- |
| remaining deliveries | workload          |
| completed deliveries | progress          |
| historical speed     | efficiency        |
| route length         | operational state |

---

## Density Features

| Feature                 | Purpose            |
| ----------------------- | ------------------ |
| nearby delivery density | congestion proxy   |
| region activity         | hotspot estimation |
| local courier frequency | operational load   |

---

# Component 5 — Route Optimization

## Objective

Generate actual travel routes between predicted delivery stops.

---

# Important Separation

## AI Model decides:

```text id="jlwm13"
WHAT order deliveries should happen
```

## Routing engine decides:

```text id="jlwm14"
HOW to travel between them
```

---

# Recommended Algorithms

## MVP

* Dijkstra
* A*
* OR-Tools TSP

---

# Input

Predicted stop sequence:

```text id="jlwm15"
Courier → A → C → B
```

---

# Output

Road-following route path.

---

# Route Data Source

Initially:

* straight-line coordinates

Advanced:

* OpenStreetMap
* OSRM
* GraphHopper

---

# Component 6 — Route Map Visualization

## Objective

Display courier routes visually.

---

# Frontend Map Stack

Recommended:

* React
* React Leaflet

---

# What the map shows

| Element          | Description             |
| ---------------- | ----------------------- |
| Courier location | current position        |
| Delivery markers | assigned stops          |
| Delivery order   | numbered markers        |
| Route polyline   | travel path             |
| ETA labels       | predicted delivery time |

---

# Backend Output Example

```json id="jlwm16"
{
  "courier_id": "C1",
  "stops": [
    {"lat":12.1,"lng":77.1,"order":1},
    {"lat":12.2,"lng":77.2,"order":2}
  ]
}
```

Frontend renders:

* markers
* connecting paths
* route overlays

---

# Component 7 — ETA Prediction

Handled by teammate’s module.

Your route pipeline will integrate:

* predicted ETAs
* delay probabilities

into:

* courier dashboard
* route scoring

---

# 5. Recommended Implementation Phases

---

# Phase 1 — MVP

## Implement:

* order clustering
* courier assignment
* OR-Tools routing
* basic map visualization

### Goal:

Functional delivery management system.

---

# Phase 2 — AI Route Prediction

## Add

* LightGBM route sequencing
* route ranking
* historical courier behavior learning

### Goal

AI-assisted delivery sequencing.

---

## Notebook: `notebooks/route_prediction_pipeline.ipynb`

Single notebook: load data → train LambdaRank on `Delivery.csv` → evaluate → save `route_ranker.pkl` / `route_ranker.lgb` → optional pkl demo. (OSRM map cells are optional; production inference uses the FastAPI service below.)

**Run from** `ml_services/route_prediction/notebooks/` so `Couriers_seg/Delivery.csv` resolves.

| Config | Purpose |
| --- | --- |
| `DEV_COURIERS = 500` | Fast dev run (~121k orders after filters) |
| `DEV_COURIERS = None` | Full filtered dataset (~444k orders) — use only after sanity passes on dev |

**Cell order:** train → Hit@1 → `RoutePredictor` → metric summary → **sanity checks** (`READY_FOR_FULL_TRAIN`) → save `route_ranker.pkl` (blocked if sanity fails) → optional pkl reload demo.

**Sanity checks (before pkl / full train):** temporal split; no forbidden features; Hit@1 vs nearest-neighbor; ablations (wait features, `poi_lat`/`poi_lng`); metrics below leaky v2 ceilings (Hit@1 &lt; 0.92, τ &lt; 0.82). Step Hit@1 can still be high (~0.85–0.89) with known addresses — that is not the same as v2 `duration_min` leakage. Set `DEV_COURIERS = None` only when `READY_FOR_FULL_TRAIN` is `True`.

---

## Leakage fix (v3 — current pipeline)

Earlier runs inflated metrics (~**95%** Hit@1, ~**0.89** Kendall τ) because the model used information not available when choosing the next stop.

| Removed (leaky) | Why |
| --- | --- |
| **`duration_min`** | Uses `sign_time − receipt_time` — completion time is unknown before delivery. |
| **`elapsed_minutes` from `sign_time`** | Training/eval advanced the route clock from actual sign-off times. |
| **Oracle greedy decode** | Same issue at route level during Kendall evaluation. |

**Still allowed:** `sign_time` is used only to (1) filter bad rows, (2) define `stop_rank` labels from historical routes — not as model inputs.

### Knowable features (v3)

| Feature | Source at decision time |
| --- | --- |
| `dist_to_candidate`, `log_dist_to_candidate` | Current courier position → candidate POI (projected units) |
| `bearing_sin`, `bearing_cos` | Direction to candidate |
| `hour_of_day`, `minute`, `is_*` | From `receipt_time` (known when order accepted) |
| `receipt_hour` | Hour order was received |
| `wait_since_receipt_min`, `log_wait_since_receipt` | Simulated route clock minus `receipt_time` |
| `elapsed_minutes` | `step × MINUTES_PER_STOP_EST` (default 8), not `sign_time` |
| `stops_completed`, `stops_remaining` | Route progress |
| `city_name_enc`, `typecode_enc`, `aoi_id_enc` | Encoded categoricals (fit on train days only) |

---

## Model metrics

| Run | Data | Hit@1 (step) | Kendall τ (greedy) | Test routes | Orders (filtered) | Best LGB iter | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **v2 (leaky)** | 500 couriers | **0.948** | **0.891** | — | ~121k | — | `duration_min` + oracle `sign_time` for elapsed |
| **v3 (honest, dev)** | 500 couriers | **0.8665** | **0.7398** | 343 | 121,431 | 1 | Step Hit@1 uses oracle position per step |
| **v3 (honest, full)** | `DEV_COURIERS=None` | **0.8911** | **0.7919** | 1,237 | 443,726 | 1 | Full filtered dataset after sanity gate |

### Dev run details (`DEV_COURIERS=500`)

| Item | Value |
| --- | --- |
| Hit@1 steps evaluated | 7,848 |
| Train `ds` | 318–331 (113,240 orders) |
| Test `ds` | 401 only (8,191 orders) |
| Cutoff | `ds < 391` train \| `ds >= 391` test |
| Order-id overlap train ∩ test | 0 |

### Full run details (`DEV_COURIERS=None`)

| Item | Value |
| --- | --- |
| Train orders | 414,291 |
| Test orders | 29,435 |
| Train routes (sample build) | 17,237 |
| Test routes | 1,237 |
| Ranking rows (train / test) | ~6.07M / ~442k |

### Sanity gate (dev run — all passed)

| Check | Result |
| --- | --- |
| `temporal_split_ok` | PASS |
| `no_forbidden_features` | PASS |
| `model_beats_nearest_neighbor` | PASS |
| `wait_features_not_dominated` | PASS |
| `hit_at_1_below_leaky_v2` | PASS |
| `kendall_below_leaky_v2` | PASS |
| `hit_at_1_above_floor` | PASS |
| `kendall_above_floor` | PASS |
| **`READY_FOR_FULL_TRAIN`** | **True** |

**Feature columns (20):** `poi_lat`, `poi_lng`, `dist_to_candidate`, `log_dist_to_candidate`, `bearing_sin`, `bearing_cos`, `hour_of_day`, `minute`, `is_morning`, `is_afternoon`, `is_evening`, `city_name_enc`, `typecode_enc`, `aoi_id_enc`, `stops_completed`, `stops_remaining`, `elapsed_minutes`, `receipt_hour`, `wait_since_receipt_min`, `log_wait_since_receipt`

**Forbidden in model:** `duration_min`, `sign_time` — not present in `FEATURE_COLS`.

**Hit@1 note:** Step-level Hit@1 uses the true courier position each step (not a full greedy rollout). Route-level Kendall τ uses greedy `predict_full_sequence`.

---

## Pipeline details (v3)

1. **Temporal split** — train `ds < 391`, test `ds >= 391`; encoders fit on train only.
2. **Full-dataset option** — `DEV_COURIERS = None` after sanity passes.
3. **LightGBM LambdaRank** — `label_gain`, `lambdarank_truncation_level=30`, up to 800 rounds, early stopping 50.
4. **Parallel sample build** — `joblib` over courier-day routes.
5. **`RoutePredictor` v3** in `route_ranker.pkl` — same feature logic as training via `augment_candidate_features()`.

**Coordinates:** `poi_lat` / `poi_lng` are Web Mercator metres (swapped labels in the CSV).

---

## Inference

| Artifact | Path | Purpose |
| --- | --- | --- |
| **`route_ranker.pkl`** | `notebooks/route_ranker.pkl` | Full v3 bundle (model + encoders) |
| **`route_predictor.py`** | package root | `RoutePredictor` + feature helpers (notebook-independent) |
| **FastAPI** | `api/main.py` | HTTP API for LangGraph / dashboard |

Train and export the pkl from `route_prediction_pipeline.ipynb` (sanity gate must pass). The API loads `notebooks/route_ranker.pkl` by default.

### Run the inference API

```bash
cd ml_services/route_prediction
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Optional env:

| Variable | Default |
| --- | --- |
| `ROUTE_RANKER_MODEL` | `notebooks/route_ranker.pkl` |

- **OpenAPI docs:** http://localhost:8000/docs  
- **Health:** `GET /health`

### HTTP endpoints

#### `GET /health`

Returns model version and path.

```json
{
  "status": "ok",
  "model_version": "3.0",
  "model_path": ".../notebooks/route_ranker.pkl",
  "feature_count": 20
}
```

---

#### `POST /predict/next-stop`

Pick the best next delivery from a list of remaining stops.

**Request body**

| Field | Type | Description |
| --- | --- | --- |
| `current_lat` | float | Courier position (Web Mercator) |
| `current_lng` | float | Courier position (Web Mercator) |
| `stops_completed` | int | Deliveries already done on this route (`0` = first stop) |
| `route_start_time` | ISO datetime | Route clock anchor (usually hub / first `receipt_time`) |
| `remaining_orders` | array | Stops not yet visited (see order object below) |

**Response**

| Field | Description |
| --- | --- |
| `order_id` | Predicted next stop |
| `candidate_scores` | `{order_id, score}` for each remaining stop |
| `chosen` | `order_id`, `poi_lat`, `poi_lng`, distance / stops_remaining |

---

#### `POST /predict/route`

Greedy full-route sequence for one courier run.

**Request body**

| Field | Type | Description |
| --- | --- | --- |
| `orders` | array | All stops on the route (min 1); **first row** = start `receipt_lat` / `receipt_lng` / `route_start_time` |

**Response**

```json
{ "sequence": ["order_id_1", "order_id_2", "..."] }
```

---

### Order object (both endpoints)

Each stop in `remaining_orders` or `orders`:

| Field | Type | Required |
| --- | --- | --- |
| `order_id` | string | yes |
| `poi_lat`, `poi_lng` | float | yes |
| `receipt_time` | ISO datetime | yes |
| `receipt_lat`, `receipt_lng` | float | yes |
| `city_name` | string | yes |
| `typecode` | string | yes |
| `aoi_id` | string or int | yes |

**Do not send** `sign_time` or `duration_min` for inference (v3).

Ready-made payloads (from `Delivery.csv`) live in **`api/samples/`**:

- `api/samples/predict_route.json`
- `api/samples/predict_next_stop.json`

### Sample JSON: `POST /predict/route`

Three Shanghai stops; **first order** is the route start (`receipt_lat` / `receipt_lng` / `route_start_time` anchor). Coordinates are Web Mercator metres (same as training CSV).

```json
{
  "orders": [
    {
      "order_id": "687227b4d0c733049b16ccd566db6e01",
      "poi_lat": -7458320.990216101,
      "poi_lng": 10563512.485412452,
      "receipt_time": "1900-03-18T13:35:00",
      "receipt_lat": -7457997.840960964,
      "receipt_lng": 10561603.356145348,
      "city_name": "Shanghai",
      "typecode": "4602b38053ece07a9ca5153f1df2e404",
      "aoi_id": "e0581ca18e7ca371a9869e041cb09075"
    },
    {
      "order_id": "ee46cae9ba2c002451af3c6fbcb49410",
      "poi_lat": -7467396.967579869,
      "poi_lng": 10581305.792820849,
      "receipt_time": "1900-03-18T13:02:00",
      "receipt_lat": -7467606.594505412,
      "receipt_lng": 10581244.567100914,
      "city_name": "Shanghai",
      "typecode": "203ac3454d75e02ebb0a3c6f51d735e4",
      "aoi_id": "4de9bf7f155046e7d0fd400672ab9cf3"
    },
    {
      "order_id": "38912be86c83138901b5e26398832be7",
      "poi_lat": -7456804.199777879,
      "poi_lng": 10562727.683002362,
      "receipt_time": "1900-03-18T12:11:00",
      "receipt_lat": -7457996.537922548,
      "receipt_lng": 10561604.469340254,
      "city_name": "Shanghai",
      "typecode": "203ac3454d75e02ebb0a3c6f51d735e4",
      "aoi_id": "fe48cde9b33e2308641d985f8a701c7e"
    }
  ]
}
```

**Example response**

```json
{
  "sequence": [
    "687227b4d0c733049b16ccd566db6e01",
    "38912be86c83138901b5e26398832be7",
    "ee46cae9ba2c002451af3c6fbcb49410"
  ]
}
```

(Order within `sequence` depends on the loaded model; shape is always `N` ids for `N` input stops.)

---

### Sample JSON: `POST /predict/next-stop`

Courier at the hub (first stop’s `receipt_lat` / `receipt_lng`); all three stops still undelivered.

```json
{
  "current_lat": -7457997.840960964,
  "current_lng": 10561603.356145348,
  "stops_completed": 0,
  "route_start_time": "1900-03-18T13:35:00",
  "remaining_orders": [
    {
      "order_id": "687227b4d0c733049b16ccd566db6e01",
      "poi_lat": -7458320.990216101,
      "poi_lng": 10563512.485412452,
      "receipt_time": "1900-03-18T13:35:00",
      "receipt_lat": -7457997.840960964,
      "receipt_lng": 10561603.356145348,
      "city_name": "Shanghai",
      "typecode": "4602b38053ece07a9ca5153f1df2e404",
      "aoi_id": "e0581ca18e7ca371a9869e041cb09075"
    },
    {
      "order_id": "ee46cae9ba2c002451af3c6fbcb49410",
      "poi_lat": -7467396.967579869,
      "poi_lng": 10581305.792820849,
      "receipt_time": "1900-03-18T13:02:00",
      "receipt_lat": -7467606.594505412,
      "receipt_lng": 10581244.567100914,
      "city_name": "Shanghai",
      "typecode": "203ac3454d75e02ebb0a3c6f51d735e4",
      "aoi_id": "4de9bf7f155046e7d0fd400672ab9cf3"
    },
    {
      "order_id": "38912be86c83138901b5e26398832be7",
      "poi_lat": -7456804.199777879,
      "poi_lng": 10562727.683002362,
      "receipt_time": "1900-03-18T12:11:00",
      "receipt_lat": -7457996.537922548,
      "receipt_lng": 10561604.469340254,
      "city_name": "Shanghai",
      "typecode": "203ac3454d75e02ebb0a3c6f51d735e4",
      "aoi_id": "fe48cde9b33e2308641d985f8a701c7e"
    }
  ]
}
```

**Example response**

```json
{
  "order_id": "38912be86c83138901b5e26398832be7",
  "candidate_scores": [
    { "order_id": "687227b4d0c733049b16ccd566db6e01", "score": 0.12 },
    { "order_id": "ee46cae9ba2c002451af3c6fbcb49410", "score": 0.08 },
    { "order_id": "38912be86c83138901b5e26398832be7", "score": 0.45 }
  ],
  "chosen": {
    "order_id": "38912be86c83138901b5e26398832be7",
    "poi_lat": -7456804.199777879,
    "poi_lng": 10562727.683002362,
    "dist_to_candidate": 1234.5,
    "stops_remaining": 3
  }
}
```

(`score` values are illustrative; your model returns real floats.)

---

### curl (using sample files)

From `ml_services/route_prediction`:

```bash
# Health
curl http://localhost:8000/health

# Full route
curl -X POST http://localhost:8000/predict/route \
  -H "Content-Type: application/json" \
  -d @api/samples/predict_route.json

# Next stop
curl -X POST http://localhost:8000/predict/next-stop \
  -H "Content-Type: application/json" \
  -d @api/samples/predict_next_stop.json
```

**PowerShell**

```powershell
Invoke-RestMethod -Uri http://localhost:8000/predict/route -Method Post `
  -ContentType "application/json" `
  -Body (Get-Content api/samples/predict_route.json -Raw)
```

### Python module (no HTTP)

```python
from pathlib import Path
import pandas as pd
from route_predictor import RoutePredictor, orders_to_dataframe

predictor = RoutePredictor.load(Path("notebooks/route_ranker.pkl"))

# From list of dicts (same shape as API JSON)
orders = [...]
route_df = orders_to_dataframe(orders)
sequence = predictor.predict_full_sequence(route_df)

# Next stop only
order_id, scores, row = predictor.predict_next_stop(
    current_lat, current_lng, route_df, stops_completed=0,
    route_start_time=pd.Timestamp(orders[0]["receipt_time"]),
)
```

### Integrations

| Consumer | Usage |
| --- | --- |
| **LangGraph agent** | `POST /predict/next-stop` or `/predict/route` with tool payloads matching the order object |
| **Frontend dashboard** | Same endpoints; poll `GET /health` for readiness |

---

# Phase 3 — Operational Intelligence

## Add:

* congestion-aware routing
* dynamic reassignment
* delay prediction integration

### Goal:

Realistic logistics optimization.

---

# Phase 4 — Advanced AI Extensions

Optional future upgrades:

| Upgrade                          | Technology             |
| -------------------------------- | ---------------------- |
| Graph-based routing intelligence | Graph Neural Networks  |
| Dynamic congestion forecasting   | STG models             |
| Adaptive dispatching             | Reinforcement Learning |
| Live traffic integration         | Real-time APIs         |

---

# 6. Recommended Tech Stack

| Component            | Technology      |
| -------------------- | --------------- |
| Backend API          | FastAPI         |
| ML Models            | LightGBM        |
| Data Processing      | Pandas          |
| Spatial Processing   | Geopy           |
| Optimization         | OR-Tools        |
| Graph Routing        | NetworkX        |
| Visualization        | React + Leaflet |
| Future Deep Learning | PyTorch         |

---

# 7. Recommended Folder Structure

**Target layout (full platform):**

```text
project/
├── data/
├── models/
├── notebooks/
├── outputs/
├── src/
│   ├── clustering/
│   ├── assignment/
│   ├── routing/
│   ├── prediction/
│   ├── visualization/
│   └── api/
├── frontend/
└── training/
```

**Current `ml_services/route_prediction/` layout (implemented):**

```text
route_prediction/
├── api/
│   ├── main.py              # FastAPI inference service
│   ├── schemas.py           # Request/response models
│   └── samples/             # predict_route.json, predict_next_stop.json
├── notebooks/
│   ├── route_prediction_pipeline.ipynb
│   ├── route_ranker.pkl     # exported after training
│   ├── route_ranker.lgb
│   └── Couriers_seg/        # Delivery.csv, etc.
├── route_predictor.py       # RoutePredictor v3 + feature helpers
├── requirements.txt
└── README.md
```

---

# 8. Recommended Model Pipeline

---

# Step 1 — Data Preprocessing

Tasks:

* clean timestamps
* normalize coordinates
* reconstruct courier routes
* generate training sequences

---

# Step 2 — Feature Engineering

Generate:

* spatial features
* temporal features
* courier-state features
* congestion proxies

---

# Step 3 — Train LightGBM Ranker

Input:

```text id="jlwm18"
courier state + candidate deliveries
```

Output:

```text id="jlwm19"
next delivery ranking
```

---

# Step 4 — Route Generation

Combine:

* predicted delivery order
* shortest-path routing

to generate final route.

---

# Step 5 — Dashboard Rendering

Display:

* courier route
* stop order
* ETA
* delivery information

---

# 9. Why This Project Is Strong

This project combines:

| Capability                         | Included |
| ---------------------------------- | -------- |
| Spatial clustering                 | Yes      |
| Route prediction                   | Yes      |
| Courier dispatching                | Yes      |
| Optimization                       | Yes      |
| AI ranking                         | Yes      |
| Operational logistics intelligence | Yes      |
| Visualization                      | Yes      |

This makes it significantly stronger than:

* simple routing apps
* basic ML projects
* isolated ETA prediction systems

because it models:

```text id="jlwm20"
real-world logistics operations
```

rather than only shortest paths or static forecasting.