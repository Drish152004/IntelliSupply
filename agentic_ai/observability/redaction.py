"""Reusable payload redaction for orchestration observability logs."""

from __future__ import annotations

from typing import Any

SENSITIVE_KEY_FRAGMENTS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "secret",
        "credential",
        "credentials",
        "authorization",
        "auth_header",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "bearer",
        "private_key",
        "session_token",
        "client_secret",
    }
)

MAX_VALUE_LEN = 300
MAX_SAMPLE_ROWS = 5
MAX_ANSWER_PREVIEW = 500


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def redact_value(key: str, value: Any) -> Any:
    """Recursively redact sensitive values in nested structures."""
    if is_sensitive_key(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {k: redact_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(str(index), item) for index, item in enumerate(value)]
    if isinstance(value, tuple):
        return [redact_value(str(index), item) for index, item in enumerate(value)]
    return value


def redact_payload(payload: Any) -> Any:
    """Redact a payload object (dict, list, or scalar)."""
    if isinstance(payload, dict):
        return {k: redact_value(k, v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [redact_value(str(i), item) for i, item in enumerate(payload)]
    return payload


def truncate_text(text: str, max_len: int = MAX_VALUE_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
