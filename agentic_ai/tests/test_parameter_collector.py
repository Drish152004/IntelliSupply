"""Tests for one-by-one parameter collection."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.parameter_collector import (
    finalize_partial,
    next_collection_step,
    parse_field_answer,
)


def test_eta_collects_fields_in_order() -> None:
    partial: dict = {}
    tool = "predict_eta"
    step = next_collection_step(tool, partial)
    assert step is not None
    path, _ = step
    parse_field_answer(tool, partial, path, "12345")
    step = next_collection_step(tool, partial)
    assert step is not None
    assert step[0] == "from_dipan_id"


def test_eta_finalize() -> None:
    partial = {
        "delivery_user_id": 1,
        "from_dipan_id": 2,
        "aoi_id": 3,
        "receipt_time": "2024-01-01T12:00:00",
        "receipt_lat": 1.0,
        "receipt_lng": 2.0,
        "poi_lat": 3.0,
        "poi_lng": 4.0,
    }
    assert next_collection_step("predict_eta", partial) is None
    out = finalize_partial("predict_eta", partial)
    assert out["delivery_user_id"] == 1
