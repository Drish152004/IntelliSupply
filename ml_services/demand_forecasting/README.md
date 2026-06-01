# Demand forecasting (inference only)

Self-contained ML inference package for your team. No training code or LaDe dataset included.

## Contents

```
ml_services/demand_forecasting/
  models/lade_demand_forecaster.pkl   # trained sklearn pipeline + metadata
  api/app.py                          # FastAPI service
  inference.py                          # load pkl + predict()
  run_api.py                            # start server
  requirements.txt
```

## Install & run

```bash
pip install -r ml_services/demand_forecasting/requirements.txt
python ml_services/demand_forecasting/run_api.py
```

Open http://127.0.0.1:8000/docs

## Integrate from backend

**POST** `/predict`

```json
{
  "records": [
    {
      "city": "Hangzhou",
      "region_id": "56",
      "day_of_week": 2,
      "month": 11,
      "day_of_month": 5,
      "day_of_year": 309,
      "is_weekend": 0,
      "lag_1": 120,
      "lag_2": 115,
      "lag_7": 98,
      "lag_14": 105,
      "rolling_mean_7": 110,
      "rolling_std_7": 25,
      "rolling_mean_28": 108
    }
  ]
}
```

**Response:** `{ "predictions": [{ "predicted_demand": 118.4, ... }] }`

**GET** `/meta` — feature column names and holdout metrics (MAE, RMSE, MAPE, R²).

## Python (no HTTP)

```python
import pickle
from pathlib import Path

pkl = Path("ml_services/demand_forecasting/models/lade_demand_forecaster.pkl")
with pkl.open("rb") as f:
    bundle = pickle.load(f)

model = bundle["model"]
feature_cols = bundle["feature_cols"]
# model.predict(df[feature_cols])
```

## Required input features

| Column | Type | Description |
|--------|------|-------------|
| city | string | e.g. Hangzhou |
| region_id | string | Region id |
| day_of_week | int 0-6 | Monday=0 |
| month | int 1-12 | |
| day_of_month | int | |
| day_of_year | int | |
| is_weekend | int 0/1 | |
| lag_1, lag_2, lag_7, lag_14 | float | Past demand |
| rolling_mean_7, rolling_std_7, rolling_mean_28 | float | Rolling stats |

Your app must compute lags/rolling features from historical demand before calling the API.
