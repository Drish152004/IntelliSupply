"""Single entry point for loading environment variables."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from config.paths import ENV_FILE

_loaded = False


def load_env(*, override: bool = False) -> Path:
    """Load REPO_ROOT/.env once; return path used."""
    global _loaded
    if _loaded and not override:
        return ENV_FILE
    if ENV_FILE.is_file():
        load_dotenv(ENV_FILE, override=override)
    else:
        load_dotenv(override=override)
    _loaded = True
    return ENV_FILE
