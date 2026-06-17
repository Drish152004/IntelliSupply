"""State size metrics for orchestration observability."""

from __future__ import annotations

import json
from typing import Any

from observability.redaction import redact_payload


def _estimate_size_bytes(value: Any) -> int:
    try:
        return len(json.dumps(value, default=str, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        return len(repr(value).encode("utf-8"))


def compute_state_metrics(state: dict[str, Any]) -> dict[str, Any]:
    """Compute lightweight size metrics for an orchestrator state snapshot."""
    keys = sorted(state.keys())
    message_count = 0
    for key in ("agent_response", "final_response"):
        if state.get(key):
            message_count += 1

    return {
        "state_keys": keys,
        "estimated_state_size_bytes": _estimate_size_bytes(redact_payload(state)),
        "message_count": message_count,
    }
