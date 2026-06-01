# GraphDB (Neo4j + GraphRAG)

Logistics knowledge graph loaded from Supabase Postgres into Neo4j, queried via natural language (Cypher generation + LLM answer).

## No Neo4j yet?

You do **not** need a graph to run the LangGraph agent. Until Neo4j is loaded, logistics questions fall back to **route/ETA ML** (`graph_used: false` in the JSON response).

To enable GraphRAG, complete **First-time setup** below once.

## First-time setup (Neo4j Desktop on Windows)

### A. Install and start Neo4j

1. Download [Neo4j Desktop](https://neo4j.com/download/) and install it.
2. **New** → **Create project** (any name, e.g. IntelliSupply).
3. **Add** → **Local DBMS** → pick a version (5.x recommended) → set a **password** (remember it).
4. **Start** the DBMS (green play button). Bolt should be `bolt://localhost:7687`.
5. **Create database** (Neo4j 5+):
   - Open the DBMS → **Databases** tab → **Create database**
   - Name: `intellisupply` (must match `NEO4J_DATABASE` in `.env`)
   - Or use the default database `neo4j` and set `NEO4J_DATABASE=neo4j` in `.env` instead.

### B. Configure `.env`

In this folder, copy `.env.example` to `.env` and set:

- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=` the password from step A3
- `NEO4J_DATABASE=intellisupply` (or `neo4j` if you skipped creating a named DB)
- Supabase variables from your project (**Settings → Database** in Supabase dashboard)
- `NVIDIA_API_KEY` from [NVIDIA API](https://build.nvidia.com/) (for GraphRAG questions only; not needed for `load_graph`)

### C. Install Python deps and load data

```powershell
cd C:\Users\Relanto\IntelliSupply
pip install -r rag\requirements.txt

cd rag
python -m graphdb.create_constraints
python -m graphdb.load_graph
```

`load_graph` reads tables from **Supabase Postgres** and writes nodes/relationships into Neo4j. It can take a while; you need working Supabase credentials and network access.

### D. Verify

```powershell
cd rag
python -m graphdb.graph_rag
```

Ask: `How many hubs are in Shanghai?` — you should get Cypher + an answer.

In Neo4j Browser (open from Desktop → **Open**), run:

```cypher
MATCH (n) RETURN labels(n) AS label, count(*) AS c ORDER BY c DESC LIMIT 10
```

If counts are > 0, the graph is loaded.

### E. Use with the agent

```powershell
cd agentic_ai
python main.py
```

Ask a logistics / hub / city question — response should include `"source": "graphdb"` and `"graph_used": true`.

## Prerequisites

- **Neo4j Desktop** (or Docker): create a database named `intellisupply` (must match `NEO4J_DATABASE`).
- **Python 3.12+** with packages: `neo4j`, `pandas`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`, `openai`
- **Supabase** Postgres credentials (for one-time load)
- **NVIDIA API key** (for `graph_rag.py` — Cypher and answer generation)

```bash
pip install neo4j pandas sqlalchemy psycopg2-binary python-dotenv openai
```

## Environment (`.env` in this folder)

Copy `.env.example` or a teammate template. **Do not commit `.env`.**

| Variable | Description |
|----------|-------------|
| `NEO4J_URI` | Bolt URL, e.g. `bolt://localhost:7687` |
| `NEO4J_USER` | Usually `neo4j` |
| `NEO4J_PASSWORD` | Your local Neo4j password |
| `NEO4J_DATABASE` | Database name, e.g. `intellisupply` |
| `SUPABASE_DB_HOST` | Supabase pooler host |
| `SUPABASE_DB_PORT` | `6543` (pooler) or `5432` (direct) |
| `SUPABASE_DB_NAME` | Usually `postgres` |
| `SUPABASE_DB_USER` | Often `postgres.<project-ref>` |
| `SUPABASE_DB_PASSWORD` | Supabase database password |
| `NVIDIA_API_KEY` | NVIDIA NIM / integrate API key |
| `GRAPH_LLM_MODEL` | e.g. `meta/llama-3.1-8b-instruct` |

`GOOGLE_CLIENT_ID` / `client_secret` are unused by current scripts and can be omitted.

## Load graph (run from `rag/`)

```powershell
cd path\to\IntelliSupply\rag

python -m graphdb.clear_graph          # optional: wipe existing data
python -m graphdb.create_constraints
python -m graphdb.load_graph
```

`load_graph.py` loads cities, couriers, hubs, hub metrics, hub routes, grid routes, and pickup orders. Delivery orders and courier segments are **not** loaded by default (see `load_all()` in `load_graph.py`).

## Verify GraphRAG CLI

```powershell
cd rag
python -m graphdb.graph_rag
```

Example questions: “How many hubs are in Shanghai?”, “List hubs with highest delivery count.”

Sample Cypher: `cypher/sample_queries.cypher`. Neo4j Browser: http://localhost:7474

## Agent integration

`agentic_ai` logistics agent calls `ask_graph()` first; if the graph has no useful answer, it falls back to route/ETA ML inference. See `agentic_ai/integrations/graph_bridge.py`.
