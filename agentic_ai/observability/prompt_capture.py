"""DEBUG-only prompt file capture for orchestration runs."""

from __future__ import annotations

import os
from pathlib import Path

from config.paths import REPO_ROOT

_PROMPT_DIR_ENV = "ORCHESTRATOR_PROMPT_DIR"
_DEBUG_ENV = "ORCHESTRATOR_DEBUG"


def is_debug_mode() -> bool:
    """Return True when orchestrator DEBUG observability mode is enabled."""
    return os.getenv(_DEBUG_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def prompt_capture_enabled() -> bool:
    """Prompt files are written only in DEBUG mode."""
    return is_debug_mode()


def prompt_dir() -> Path:
    configured = os.getenv(_PROMPT_DIR_ENV, "").strip()
    if configured:
        return Path(configured)
    return REPO_ROOT / "logs" / "prompts"


def capture_prompt(trace_id: str, label: str, content: str) -> Path | None:
    """
    Write a prompt file when DEBUG mode is enabled.

    Returns the written path, or None when capture is disabled.
    """
    if not prompt_capture_enabled():
        return None

    directory = prompt_dir()
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{trace_id}_{label}.txt"
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path
