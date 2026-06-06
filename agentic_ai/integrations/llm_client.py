"""Shared OpenAI client for agentic_ai (NVIDIA API)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_ENV = REPO_ROOT / "rag" / "graphdb" / ".env"
INVENTORY_ENV = REPO_ROOT / "rag" / "inventory" / ".env"

_env_loaded = False
_client: OpenAI | None = None


def ensure_env() -> None:
    global _env_loaded
    if not _env_loaded:
        if RAG_ENV.is_file():
            load_dotenv(RAG_ENV)
        if INVENTORY_ENV.is_file():
            load_dotenv(INVENTORY_ENV)
        _env_loaded = True


def get_client() -> OpenAI:
    global _client
    ensure_env()
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("NVIDIA_API_KEY"),
            base_url="https://integrate.api.nvidia.com/v1",
        )
    return _client


def get_model() -> str:
    ensure_env()
    return os.getenv("GRAPH_LLM_MODEL", "meta/llama-3.1-8b-instruct")
