"""Detect missing required fields in an ML payload."""

from __future__ import annotations


class MissingFieldDetector:
    """Compare a payload against required fields and return gaps."""

    @staticmethod
    def detect(required_fields: frozenset[str], payload: dict) -> list[str]:
        missing: list[str] = []
        for field in sorted(required_fields):
            value = payload.get(field)
            if value is None or value == "":
                missing.append(field)
        return missing
