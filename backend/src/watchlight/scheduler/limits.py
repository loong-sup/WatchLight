from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchlight.storage.repos.tasks import TasksRepo


@dataclass(frozen=True, slots=True)
class LimitResult:
    allowed: bool
    reason: str | None = None


class Limits:
    def __init__(self, *, max_tasks_per_user: int = 20, max_concurrent_global: int = 4) -> None:
        self.max_tasks_per_user = max_tasks_per_user
        self.max_concurrent_global = max_concurrent_global

    def check_task(self, repo: TasksRepo) -> LimitResult:
        if len(repo.list()) >= self.max_tasks_per_user:
            return LimitResult(False, "task_limit_reached")
        return LimitResult(True)

    def check_concurrency(self, running_count: int) -> LimitResult:
        if running_count >= self.max_concurrent_global:
            return LimitResult(False, "global_concurrency_limit_reached")
        return LimitResult(True)
