"""Generic cache service with swappable backends."""

from __future__ import annotations

from typing import Any, Protocol

from cache.memory_cache import MemoryCache
from orchestrator.task_registry import ttl_for_task


class CacheBackend(Protocol):
    """Protocol for cache storage backends."""

    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl: int) -> None: ...

    def delete(self, key: str) -> bool: ...

    def clear(self) -> None: ...

    def stats(self) -> dict[str, int]: ...


class CacheService:
    """Facade over a cache backend with task-aware TTL helpers."""

    def __init__(self, backend: CacheBackend | None = None) -> None:
        self._backend: CacheBackend = backend or MemoryCache()

    def get(self, key: str) -> Any | None:
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._backend.set(key, value, ttl)

    def set_for_task(self, key: str, value: Any, task: str) -> None:
        ttl = ttl_for_task(task)
        if ttl is None:
            return
        self.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        return self._backend.delete(key)

    def clear(self) -> None:
        self._backend.clear()

    def stats(self) -> dict[str, int]:
        return self._backend.stats()
