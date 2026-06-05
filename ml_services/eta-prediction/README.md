# ETA Prediction System

A modular LightGBM-based ETA prediction system featuring an automated, sequential training pipeline and a live FastAPI inference service.

---

## Project Structure

```text
eta_prediction/
├── api/
│   ├── main.py            # FastAPI application routes
│   └── schemas.py         # Request models/schemas
├── data/
│   └── Delivery.csv       # Raw delivery dataset
├── full_pipeline/
│   ├── preprocess.py      # Data ingestion and raw preprocessing
│   ├── feature_engineering.py  # Statistical features & shared builder
│   ├── training.py        # LightGBM training loop and evaluation
│   ├── run_pipeline.py    # Sequential pipeline orchestrator
│   └── inference.py       # ETA inference entrypoint for FastAPI
├── models/                # Trained LightGBM model & serialized statistics
└── requirements.txt       # Project dependencies
```

---

## Setup Instructions

1. **Set up virtual environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate the environment**:
   *   **PowerShell**: `venv\Scripts\Activate.ps1`
   *   **Windows Command Prompt**: `venv\Scripts\activate.bat`
   *   **Linux/macOS**: `source venv/bin/activate`

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 1. Run the Training Pipeline

The training pipeline performs preprocessing, compiles historical courier/AOI statistics, fits a LightGBM regressor, and updates the models in the `models/` directory.

To run the complete pipeline:
```bash
python -m full_pipeline.run_pipeline
```

*Optional arguments:*
*   `--data-path`: Specify a custom path to the raw delivery data CSV (default: `data/Delivery.csv`).
*   `--models-dir`: Specify a custom path to save model artifacts (default: `models`).

---

## 2. Run the FastAPI Application

The live FastAPI app loads the serialized artifacts to perform real-time ETA predictions.

To start the API server locally:
```bash
uvicorn api.main:app --reload
```

*   **API Root**: `http://127.0.0.1:8000/`
*   **Interactive Docs (Swagger UI)**: `http://127.0.0.1:8000/docs`

### Example Prediction Request
Send a `POST` request to `/predict` using curl or PowerShell:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -Body '{"delivery_user_id": "0008c2b6a2314db8715301b7eeeebc5a", "from_dipan_id": "1", "aoi_id": "2", "receipt_time": "2026-06-05T12:00:00", "receipt_lat": 30.6, "receipt_lng": 104.0, "poi_lat": 30.61, "poi_lng": 104.01}' -ContentType "application/json"
```