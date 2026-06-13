"""Semantic similarity cache using normalized token vectors and cosine similarity."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import threading
from collections import Counter
from typing import Any

from orchestrator.task_registry import ttl_for_task

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.88
_DEFAULT_MAX_ENTRIES = 500


def _enabled() -> bool:
    return os.getenv("SEMANTIC_CACHE_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _threshold() -> float:
    try:
        return float(os.getenv("SEMANTIC_CACHE_THRESHOLD", str(_DEFAULT_THRESHOLD)))
    except ValueError:
        return _DEFAULT_THRESHOLD


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _token_vector(text: str) -> dict[str, float]:
    tokens = _normalize(text).split()
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = float(len(tokens))
    return {token: count / total for token, count in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class _CacheEntry:
    __slots__ = ("key", "vector", "value", "task", "role", "domain", "expires_at")

    def __init__(
        self,
        key: str,
        vector: dict[str, float],
        value: Any,
        task: str,
        role: str,
        domain: str,
        expires_at: float,
    ) -> None:
        self.key = key
        self.vector = vector
        self.value = value
        self.task = task
        self.role = role
        self.domain = domain
        self.expires_at = expires_at


class SemanticCache:
    """In-memory semantic cache with TTL per task."""

    def __init__(self) -> None:
        self._entries: list[_CacheEntry] = []
        self._lock = threading.Lock()
        self._max_entries = int(os.getenv("SEMANTIC_CACHE_MAX_ENTRIES", str(_DEFAULT_MAX_ENTRIES)))

    def _build_key(self, query: str, role: str, domain: str) -> str:
        raw = f"{_normalize(query)}|{role}|{domain}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def lookup(
        self,
        query: str,
        *,
        role: str = "",
        domain: str = "",
        task: str = "",
    ) -> tuple[bool, str | None, Any | None]:
        if not _enabled():
            return False, None, None

        vector = _token_vector(query)
        now = __import__("time").time()
        threshold = _threshold()

        with self._lock:
            best_score = 0.0
            best_entry: _CacheEntry | None = None
            alive: list[_CacheEntry] = []

            for entry in self._entries:
                if entry.expires_at <= now:
                    continue
                alive.append(entry)
                if role and entry.role and entry.role != role:
                    continue
                if domain and entry.domain and entry.domain != domain:
                    continue
                score = _cosine(vector, entry.vector)
                if score >= threshold and score > best_score:
                    best_score = score
                    best_entry = entry

            self._entries = alive

            if best_entry:
                logger.debug("Semantic cache hit score=%.3f key=%s", best_score, best_entry.key)
                return True, best_entry.key, best_entry.value

        return False, None, None

    def store(
        self,
        query: str,
        value: Any,
        *,
        role: str = "",
        domain: str = "",
        task: str = "",
    ) -> str | None:
        if not _enabled():
            return None

        ttl = ttl_for_task(task) if task else 300
        if ttl is None:
            return None

        key = self._build_key(query, role, domain)
        vector = _token_vector(query)
        now = __import__("time").time()

        entry = _CacheEntry(
            key=key,
            vector=vector,
            value=value,
            task=task,
            role=role,
            domain=domain,
            expires_at=now + ttl,
        )

        with self._lock:
            self._entries = [e for e in self._entries if e.key != key]
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries.sort(key=lambda e: e.expires_at)
                self._entries = self._entries[-self._max_entries :]

        logger.debug("Semantic cache store key=%s task=%s", key, task)
        return key


_semantic_cache: SemanticCache | None = None


def get_semantic_cache() -> SemanticCache:
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache()
    return _semantic_cache
