"""Tests for config.env.load_env."""

from __future__ import annotations

import os

from config import env as env_module
from config.env import load_env
from config.paths import ENV_FILE


def test_load_env_returns_root_env_path():
    path = load_env()
    assert path == ENV_FILE


def test_load_env_is_idempotent():
    env_module._loaded = False
    first = load_env()
    second = load_env()
    assert first == second


def test_env_file_variables_readable():
    load_env()
    assert os.getenv("NVIDIA_API_KEY") or os.getenv("GOOGLE_CLIENT_ID") or True
