# Unified ML API (`fastapi/`)

Single FastAPI gateway for all IntelliSupply ML services. Run with `app_dir` so this folder does not shadow the installed `fastapi` package.

## Run

From repo root (recommended):

```bash
pip install -r fastapi/requirements.txt
python fastapi/run.py
```

Or with reload from the `fastapi/` directory:

```bash
cd fastapi
uvicorn main:app --reload
```

From repo root without `cd`:

```bash
uvicorn main:app --reload --app-dir fastapi
```

Open http://127.0.0.1:8000/docs

### Port already in use (Windows error 10048)

Another process is bound to port 8000 (often a previous `uvicorn` or `python fastapi/run.py`). Stop it or use another port:

```powershell
# Find PID using port 8000
netstat -ano | findstr :8000
# Stop that PID (replace 12345)
taskkill /PID 12345 /F

# Or run on a different port
$env:PORT=8001; python fastapi/run.py
```

### Demand forecasting

`/demand` proxies inference to the **Hugging Face Space** (same as the agent orchestrator). Set `HF_TOKEN` if the Space is private; optional override via `HF_DEMAND_FORECAST_URL`.

See [models/hf_client.py](../models/hf_client.py).

## Endpoints

| Prefix | Description |
|--------|-------------|
| `GET /health` | All services load status |
| `/route` | Route ranker — next stop & full sequence |
| `/demand` | Regional demand forecasting |
| `/eta` | Delivery ETA (minutes) |

Legacy per-service apps under `ml_services/eta-prediction/` remain for reference; prefer this gateway.

## Agent integration

`agentic_ai` agents call the same inference code via `fastapi/services/` (in-process). Sample JSON under `fastapi/samples/` is used when queries are natural language only.
