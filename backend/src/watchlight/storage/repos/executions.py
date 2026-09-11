from __future__ import annotations

import json
from typing import Any

from watchlight.storage.repos import Repo, row_dict
from watchlight.storage.store import Store, new_id, utc_now


class ExecutionsRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> ExecutionsRepo:
        return cls(store, user_id)

    def insert(
        self,
        task_id: str,
        task_version_id: str,
        scheduled_at: int,
        *,
        triggered_by: str = "cron",
    ) -> dict[str, Any]:
        execution_id = new_id()
        self.store.execute(
            "INSERT INTO executions(execution_id,task_id,user_id,task_version_id,scheduled_at,"
            "status,triggered_by,status_history_json) VALUES (?,?,?,?,?,'pending',?,'[]')",
            (execution_id, task_id, self.user_id, task_version_id, scheduled_at, triggered_by),
        )
        result = self.get(execution_id)
        assert result is not None
        return result

    def get(self, execution_id: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM executions WHERE execution_id=? AND user_id=?", (execution_id,)
        )

    def list_for_task(self, task_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM executions WHERE task_id=? AND user_id=? ORDER BY scheduled_at DESC",
            (task_id,),
        )

    def list_pending(self, now: int) -> list[dict[str, Any]]:
        rows = self.store.fetchall(
            "SELECT e.* FROM executions e JOIN watch_tasks t ON t.task_id=e.task_id "
            "WHERE e.user_id=? AND e.status='pending' AND e.scheduled_at<=? "
            "AND t.status='active' ORDER BY e.scheduled_at",
            (self.user_id, now),
        )
        return [dict(row) for row in rows]

    def has_running(self, task_id: str) -> bool:
        row = self.one(
            "SELECT execution_id FROM executions WHERE task_id=? AND status='running' "
            "AND user_id=? LIMIT 1",
            (task_id,),
        )
        return row is not None

    def claim(self, execution_id: str, now: int) -> bool:
        cursor = self.store.execute(
            "UPDATE executions SET status='running',started_at=?,heartbeat_at=?,"
            "status_history_json=? WHERE execution_id=? AND status='pending' AND user_id=?",
            (now, now, json.dumps([{"status": "running", "at": now}]), execution_id, self.user_id),
        )
        return cursor.rowcount == 1

    def heartbeat(self, execution_id: str, now: int) -> None:
        self.store.execute(
            "UPDATE executions SET heartbeat_at=? WHERE execution_id=? AND user_id=?",
            (now, execution_id, self.user_id),
        )

    def update_counts(self, execution_id: str, **counts: int) -> None:
        allowed = {"source_count", "change_count", "signal_count", "delivery_count"}
        fields = [name for name in counts if name in allowed]
        if not fields:
            return
        sql = ",".join(f"{name}=?" for name in fields)
        cursor = self.store.execute(
            f"UPDATE executions SET {sql} WHERE execution_id=? AND user_id=?",
            (*(int(counts[name]) for name in fields), execution_id, self.user_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(execution_id)

    def settle(
        self,
        execution_id: str,
        status: str,
        *,
        counts: dict[str, int] | None = None,
        failure_summary: str | None = None,
        now: int | None = None,
    ) -> None:
        current = self.get(execution_id)
        if current is None:
            raise KeyError(execution_id)
        at = now or utc_now()
        history = json.loads(str(current["status_history_json"]))
        history.append({"status": status, "at": at})
        values = counts or {}
        self.store.execute(
            "UPDATE executions SET status=?,ended_at=?,source_count=?,change_count=?,"
            "signal_count=?,delivery_count=?,failure_summary=?,status_history_json=? "
            "WHERE execution_id=? AND user_id=?",
            (
                status,
                at,
                values.get("source_count", int(current["source_count"])),
                values.get("change_count", int(current["change_count"])),
                values.get("signal_count", int(current["signal_count"])),
                values.get("delivery_count", int(current["delivery_count"])),
                failure_summary,
                json.dumps(history),
                execution_id,
                self.user_id,
            ),
        )

    def recover_candidates(self, before: int) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM executions WHERE status='running' AND heartbeat_at<? AND user_id=?",
            (before,),
        )

    @staticmethod
    def owners_with_pending(store: Store, now: int) -> list[str]:
        return [
            str(row["user_id"])
            for row in store.fetchall(
                "SELECT DISTINCT user_id FROM executions "
                "WHERE status='pending' AND scheduled_at<=?",
                (now,),
            )
        ]

    @staticmethod
    def owners_with_stale_running(store: Store, before: int) -> list[str]:
        return [
            str(row["user_id"])
            for row in store.fetchall(
                "SELECT DISTINCT user_id FROM executions WHERE status='running' AND heartbeat_at<?",
                (before,),
            )
        ]

    @staticmethod
    def raw_get(store: Store, execution_id: str) -> dict[str, Any] | None:
        return row_dict(
            store.fetchone("SELECT * FROM executions WHERE execution_id=?", (execution_id,))
        )
