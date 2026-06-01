"""Tests for ML payload grounding (no invented values)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.ml_payload import resolve_ml_payload


def test_vague_eta_query_needs_input() -> None:
    resolution = resolve_ml_payload("eta", "what is the shipment eta?")
    assert not resolution.ready
    assert resolution.payload is None
    assert resolution.question
    assert resolution.partial_payload == {}


def test_strip_blocks_ungrounded_values() -> None:
    resolution = resolve_ml_payload(
        "eta",
        "what is the shipment eta?",
        prior_payload=None,
    )
    assert not resolution.ready
    if resolution.partial_payload:
        assert "delivery_user_id" not in resolution.partial_payload
