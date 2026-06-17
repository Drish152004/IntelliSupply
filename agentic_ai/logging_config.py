"""
Central logging configuration for orchestration trace output.

Configures a dedicated ``trace`` logger that appends to ``agentic_ai/app.log``
without altering console logging for other modules.
"""

from __future__ import annotations

import logging
from pathlib import Path

_TRACE_LOGGER_NAME = "trace"
_configured = False

_LOG_FILE = Path(__file__).resolve().parent / "app.log"
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_trace_logging() -> logging.Logger:
    """Configure the trace logger with append-only file output. Idempotent."""
    global _configured

    logger = logging.getLogger(_TRACE_LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(_LOG_FILE, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT))
    logger.addHandler(handler)

    _configured = True
    return logger
