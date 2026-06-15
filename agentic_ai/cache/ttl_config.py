"""Re-export from task_registry for backward compatibility."""

from orchestrator.task_registry import CACHE_TTL_BY_TASK, CACHEABLE_TASKS, ttl_for_task

__all__ = ["CACHE_TTL_BY_TASK", "CACHEABLE_TASKS", "ttl_for_task"]
