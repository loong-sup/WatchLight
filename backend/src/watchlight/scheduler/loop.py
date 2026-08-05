from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Protocol

from watchlight.storage.repos.events import EventsRepo
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.tasks import TasksRepo
from watchlight.storage.store import Store, utc_now

if TYPE_CHECKING:
    from collections.abc import Awaitable


class ExecutionRunner(Protocol):
    def run(self, execution_id: str, user_id: str) -> object | Awaitable[object]: ...


class SchedulerLoop:
    def __init__(self, store: Store, runner: ExecutionRunner | None = None) -> None:
        self.store = store
        self.runner = runner

    async def tick(self, now: int | None = None) -> list[str]:
        at = now or utc_now()
        claimed: list[str] = []
        for user_id in ExecutionsRepo.owners_with_pending(self.store, at):
            repo = ExecutionsRepo.for_user(self.store, user_id)
            for execution in repo.list_pending(at):
                execution_id = str(execution["execution_id"])
                task_id = str(execution["task_id"])
                if repo.has_running(task_id):
                    EventsRepo.for_user(self.store, user_id).insert(
                        {
                            "execution_id": execution_id,
                            "task_id": task_id,
                            "event_type": "scheduler.overlap_skipped",
                            "stage": "scheduler",
                            "payload": {"reason": "skipped overlap"},
                        }
                    )
                    continue
                if not repo.claim(execution_id, at):
                    continue
                claimed.append(execution_id)
                if self.runner is not None:
                    try:
                        result = self.runner.run(execution_id, user_id)
                        if inspect.isawaitable(result):
                            await result
                    except Exception as exc:
                        repo.settle(
                            execution_id,
                            "failed",
                            failure_summary=f"{type(exc).__name__}: {exc}",
                            now=at,
                        )
                self._schedule_next(user_id, execution, at)
        self._finish_draining()
        return claimed

    def _schedule_next(self, user_id: str, execution: dict[str, Any], now: int) -> None:
        if execution.get("triggered_by") != "cron":
            return
        task_id = str(execution["task_id"])
        task = TasksRepo.for_user(self.store, user_id).get(task_id)
        if task is None or task["status"] != "active":
            return
        already_queued = self.store.fetchone(
            "SELECT 1 FROM executions WHERE task_id=? AND user_id=? AND triggered_by='cron' "
            "AND status='pending' LIMIT 1",
            (task_id, user_id),
        )
        if already_queued is not None:
            return
        interval = int(task["frequency_seconds"])
        scheduled_at = max(now, int(execution["scheduled_at"])) + interval
        ExecutionsRepo.for_user(self.store, user_id).insert(
            task_id,
            str(task["current_version_id"]),
            scheduled_at,
            triggered_by="cron",
        )

    def _finish_draining(self) -> None:
        rows = self.store.fetchall(
            "SELECT task_id,user_id FROM watch_tasks WHERE status='draining'"
        )
        for row in rows:
            running = self.store.fetchone(
                "SELECT 1 FROM executions WHERE task_id=? AND user_id=? AND status='running'",
                (row["task_id"], row["user_id"]),
            )
            if running is not None:
                continue
            self.store.execute(
                "UPDATE executions SET status='cancelled' WHERE task_id=? AND user_id=? "
                "AND status='pending'",
                (row["task_id"], row["user_id"]),
            )
            TasksRepo.for_user(self.store, str(row["user_id"])).set_status(
                str(row["task_id"]), "deleted"
            )

    def recover(self, now: int | None = None, heartbeat_timeout: int = 600) -> list[str]:
        at = now or utc_now()
        recovered: list[str] = []
        for user_id in ExecutionsRepo.owners_with_stale_running(
            self.store, at - heartbeat_timeout
        ):
            repo = ExecutionsRepo.for_user(self.store, user_id)
            for execution in repo.recover_candidates(at - heartbeat_timeout):
                execution_id = str(execution["execution_id"])
                repo.settle(
                    execution_id,
                    "recovered",
                    failure_summary="recovered by boot",
                    now=at,
                )
                recovered.append(execution_id)
        return recovered
