"""Central role-to-task permission matrix — re-exported from task_registry."""

from orchestrator.task_registry import (
    CACHEABLE_TASKS,
    COURIER_RESOURCE_SCOPED_TASKS,
    FUTURE_LOGISTICS_ML_TASKS,
    LOGISTICS_RETRIEVAL_TASKS,
    LOGISTICS_TASKS,
    ROLE_PERMISSIONS,
    VALID_ROLES,
    VALID_TASKS as ALL_TASKS,
    is_task_allowed,
)

COURIER_SCOPED_TASKS = COURIER_RESOURCE_SCOPED_TASKS
COURIER_TASKS = ROLE_PERMISSIONS["COURIER"]
