from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from watchlight.scheduler.limits import Limits
from watchlight.scheduler.normalize import NormalizedResult, normalize
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.tasks import TasksRepo
from watchlight.storage.store import Store, utc_now

if TYPE_CHECKING:
    import builtins


@dataclass(frozen=True, slots=True)
class CreateResult:
    task_id: str | None
    normalized_summary: dict[str, Any]
    missing_fields: tuple[str, ...]
    normalized_version_id: str | None
    error: str | None = None


class TaskService:
    def __init__(self, store: Store, *, limits: Limits | None = None) -> None:
        self.store = store
        self.limits = limits or Limits()

    def create(self, user_id: str, draft: str | dict[str, Any]) -> CreateResult:
        normalized: NormalizedResult = normalize(draft)
        if normalized.unsupported_reason:
            return CreateResult(None, normalized.summary, (), None, normalized.unsupported_reason)
        if normalized.missing_fields:
            return CreateResult(None, normalized.summary, normalized.missing_fields, None)
        repo = TasksRepo.for_user(self.store, user_id)
        allowed = self.limits.check_task(repo)
        if not allowed.allowed:
            return CreateResult(None, normalized.summary, (), None, allowed.reason)
        frequency = int(normalized.summary["frequency_seconds"])
        if not 900 <= frequency <= 604800:
            return CreateResult(None, normalized.summary, (), None, "frequency_out_of_range")
        task = repo.create(normalized.summary, status="paused")
        return CreateResult(
            str(task["task_id"]),
            normalized.summary,
            (),
            str(task["current_version_id"]),
        )

    def list(self, user_id: str) -> list[dict[str, Any]]:
        return TasksRepo.for_user(self.store, user_id).list()

    def list_deletable(self, user_id: str) -> builtins.list[dict[str, Any]]:
        return [
            task
            for task in TasksRepo.for_user(self.store, user_id).list()
            if task["status"] in {"active", "paused"}
        ]

    def confirm_delete(self, user_id: str, task_id: str) -> dict[str, Any] | None:
        return TasksRepo.for_user(self.store, user_id).begin_draining(task_id)

    def confirm(
        self, user_id: str, task_id: str, normalized_version_id: str, *, now: int | None = None
    ) -> dict[str, Any]:
        tasks = TasksRepo.for_user(self.store, user_id)
        task = tasks.get(task_id)
        if task is None or str(task["current_version_id"]) != normalized_version_id:
            raise ValueError("task version changed before confirmation")
        at = now or utc_now()
        task = tasks.set_status(task_id, "active")
        ExecutionsRepo.for_user(self.store, user_id).insert(
            task_id,
            normalized_version_id,
            at + int(task["frequency_seconds"]),
            triggered_by="cron",
        )
        return task

    def update(self, user_id: str, task_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        if "frequency_seconds" in changes:
            frequency = int(changes["frequency_seconds"])
            if not 900 <= frequency <= 604800:
                raise ValueError("frequency_out_of_range")
        return TasksRepo.for_user(self.store, user_id).update(task_id, changes)

    def pause(self, user_id: str, task_id: str) -> dict[str, Any]:
        return TasksRepo.for_user(self.store, user_id).set_status(task_id, "paused")

    def resume(self, user_id: str, task_id: str) -> dict[str, Any]:
        return TasksRepo.for_user(self.store, user_id).set_status(task_id, "active")

    def delete(self, user_id: str, task_id: str) -> dict[str, Any]:
        return TasksRepo.for_user(self.store, user_id).set_status(task_id, "draining")

    def trigger_now(self, user_id: str, task_id: str, *, now: int | None = None) -> str:
        task = TasksRepo.for_user(self.store, user_id).get(task_id)
        if task is None or task["status"] != "active":
            raise ValueError("task is not active")
        execution = ExecutionsRepo.for_user(self.store, user_id).insert(
            task_id,
            str(task["current_version_id"]),
            now or utc_now(),
            triggered_by="manual",
        )
        return str(execution["execution_id"])
