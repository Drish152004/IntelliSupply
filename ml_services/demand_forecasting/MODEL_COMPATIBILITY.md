# Demand model compatibility

## What is in the file

`models/lade_demand_forecaster.pkl` is a Python **pickle** of a dict containing:

- `model` — sklearn `Pipeline` with steps `prep` (`ColumnTransformer`) + `reg` (`HistGradientBoostingRegressor`)
- `feature_cols`, `metadata`, etc.

The pipeline was **fitted and saved with scikit-learn 1.5.2** (see `InconsistentVersionWarning` mentioning `1.5.2`).

## The exact problem

Pickle stores **Python class paths and internal sklearn state**, not a portable model format. When you load the file, sklearn must reconstruct the same classes from **your installed** sklearn version.

On **Python 3.14** you typically only have **scikit-learn 1.8.x** wheels. That version:

1. **Cannot install sklearn 1.5.2** (no wheel; building from source fails on 3.14).
2. **Cannot unpickle** the saved pipeline because internal APIs changed, for example:
   - `AttributeError: module 'sklearn.compose._column_transformer' has no attribute '_RemainderColsList'`
   - `AttributeError: module 'sklearn._loss._loss' has no attribute '__pyx_unpickle_CyHalfSquaredError'`

Re-saving the pickle on 3.12 with sklearn 1.5.2 **does not help** on 3.14 — the file still contains 1.5.2 estimator objects.

## How to fix it later

Pick one:

### A. Re-export on the same runtime you use for the API (recommended)

1. Use the **same Python version** as production (e.g. 3.14) and install `scikit-learn` (e.g. 1.8).
2. **Retrain** the pipeline (or load training notebook) and save a new bundle:

   ```python
   import pickle
   bundle = {"model": fitted_pipeline, "feature_cols": [...], "metadata": {...}}
   with open("models/lade_demand_forecaster.pkl", "wb") as f:
       pickle.dump(bundle, f)
   ```

3. Restart the unified API and set `DEMAND_FORECASTING_ENABLED = True` in `agentic_ai/agents/inventory_agent.py` if you want orchestration again.

### B. One-time migration on Python 3.12 (same sklearn major as training)

1. Python **3.12** venv with **sklearn 1.5.2** — `pickle.load` the old file.
2. In that **same running process**, upgrade sklearn stepwise (1.5 → 1.6 → 1.7 → 1.8), loading and re-`pickle.dump` after each upgrade (sklearn’s documented migration path), **or** retrain on 3.12 with sklearn 1.8 and save once.
3. Deploy the new `.pkl` only on a Python/sklearn combo that can load it.

### C. Use a portable format going forward

Export to **ONNX**, **skops** (with compatible versions), or raw **LightGBM** booster + separate preprocessing code so you are not tied to sklearn pickle internals.

## Orchestration

Demand ML is **disabled** in `agentic_ai` until a compatible `lade_demand_forecaster.pkl` is in place. Route and ETA agents are unchanged.
