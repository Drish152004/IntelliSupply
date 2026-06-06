# Demand forecasting

LaDe regional package demand forecasting — training modules, full pipeline, and inference API.

## Layout

```
ml_services/demand_forecasting/
  models/                    # joblib, pkl, metadata, strategy config
  full_pipeline/
    pipeline.py              # DemandForecastPipeline (LaDe → forecast → outputs)
    run_demo.py              # CLI demo
  lade_demand.py             # data load, features, train, multistep forecast
  lade_weekly.py             # weekly aggregation helpers
  weekly_strategies.py       # daily_sum, hierarchical, backtests
  inference.py               # load_bundle, predict, forecast_demand
  api/app.py                 # standalone FastAPI (port 8000)
  run_api.py
```

## Inference only (team integration)

```bash
pip install -r ml_services/demand_forecasting/requirements.txt
python ml_services/demand_forecasting/run_api.py
```

**POST** `/predict` with pre-built feature rows (lags, rolling stats, calendar fields).

## Full pipeline (LaDe CSVs required)

Place data under `LaDe/delivery/` at repo root, or set `LADE_DATA_DIR`.

```bash
python ml_services/demand_forecasting/full_pipeline/run_demo.py
python ml_services/demand_forecasting/full_pipeline/run_demo.py --granularity weekly --horizon 4
```

Outputs: `full_pipeline/outputs/` (detail CSV, by-city, summary JSON).

## Unified orchestration API

The root `FastAPI/` service loads `models/lade_demand_forecaster.pkl` via `services/registry.py`.
