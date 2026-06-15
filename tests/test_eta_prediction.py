import pytest
import sys
from pathlib import Path

# Ensure paths are set up correctly for pytest
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root / "FastAPI") not in sys.path:
    sys.path.insert(0, str(repo_root / "FastAPI"))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from services.eta_prediction import predict_eta

def test_eta_prediction_complete_payload():
    """Verify that complete payload produces a dynamic ETA not equal to the 30.0 fallback."""
    payload = {
        "delivery_user_id": "courier-123",
        "from_dipan_id": "aoi-456",
        "aoi_id": "aoi-456",
        "receipt_time": "2026-06-14 10:00:00",
        "receipt_lat": 10.0,
        "receipt_lng": 77.0,
        "poi_lat": 13.5,
        "poi_lng": 55.1,
        "city_name": "Shanghai",
        "typecode": "standard"
    }
    result = predict_eta(payload)
    assert "eta_minutes" in result
    assert result["eta_minutes"] != 30.0
    print(f"\nDynamic ETA (complete payload): {result['eta_minutes']} min")

def test_eta_prediction_incomplete_payload():
    """Verify that incomplete payload (no city/typecode) doesn't crash and gets a dynamic prediction."""
    payload = {
        "delivery_user_id": "courier-123",
        "from_dipan_id": "aoi-456",
        "aoi_id": "aoi-456",
        "receipt_time": "2026-06-14 10:00:00",
        "receipt_lat": 13.0,
        "receipt_lng": 77.0,
        "poi_lat": 13.1,
        "poi_lng": 66.1
    }
    result = predict_eta(payload)
    assert "eta_minutes" in result
    assert result["eta_minutes"] != 30.0
    print(f"\nDynamic ETA (incomplete payload): {result['eta_minutes']} min")

