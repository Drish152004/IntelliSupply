"""Thread-safe in-memory cache backend with TTL support."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    created_at: float
    expires_at: float


class MemoryCache:
    """Simple in-memory cache with lazy TTL expiration."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "deletes": 0,
            "evictions": 0,
        }

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            if entry.expires_at <= time.time():
                del self._store[key]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None
            self._stats["hits"] += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: int) -> None:
        now = time.time()
        with self._lock:
            self._store[key] = _CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl,
            )
            self._stats["stores"] += 1

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._stats["deletes"] += 1
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                **self._stats,
                "size": len(self._store),
            }
