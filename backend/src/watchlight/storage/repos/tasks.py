from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import builtins

from watchlight.storage.repos import Repo
from watchlight.storage.store import Store, new_id, utc_now


class TasksRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> TasksRepo:
        return cls(store, user_id)

    def create(self, fields: dict[str, Any], *, status: str = "paused") -> dict[str, Any]:
        now = int(fields.get("created_at", utc_now()))
        task_id = str(fields.get("task_id") or new_id())
        version_id = new_id()
        snapshot = {
            "target": str(fields["target"]),
            "source_scope": fields["source_scope"],
            "trigger_condition": fields["trigger_condition"],
            "frequency_seconds": int(fields["frequency_seconds"]),
            "notification_policy": fields["notification_policy"],
        }
        with self.store.transaction():
            self.store.execute(
                "INSERT INTO watch_tasks(task_id,user_id,target,source_scope_json,"
                "trigger_condition_json,frequency_seconds,notification_policy_json,status,version,"
                "current_version_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    task_id,
                    self.user_id,
                    snapshot["target"],
                    json.dumps(snapshot["source_scope"], ensure_ascii=False),
                    json.dumps(snapshot["trigger_condition"], ensure_ascii=False),
                    snapshot["frequency_seconds"],
                    json.dumps(snapshot["notification_policy"], ensure_ascii=False),
                    status,
                    1,
                    version_id,
                    now,
                    now,
                ),
            )
            self.store.execute(
                "INSERT INTO watch_task_versions(version_id,task_id,user_id,version,"
                "modifier_user_id,modified_at,snapshot_json) VALUES (?,?,?,?,?,?,?)",
                (version_id, task_id, self.user_id, 1, self.user_id, now, json.dumps(snapshot)),
            )
        result = self.get(task_id)
        assert result is not None
        return result

    def get(self, task_id: str, *, include_deleted: bool = False) -> dict[str, Any] | None:
        deleted_clause = "" if include_deleted else " AND status != 'deleted'"
        return self.one(
            f"SELECT * FROM watch_tasks WHERE task_id = ? AND user_id = ?{deleted_clause}",
            (task_id,),
        )

    def list(self, status: str | None = None) -> builtins.list[dict[str, Any]]:
        if status:
            return self.all(
                "SELECT * FROM watch_tasks WHERE status = ? AND user_id = ? "
                "ORDER BY updated_at DESC",
                (status,),
            )
        return self.all(
            "SELECT * FROM watch_tasks WHERE status != 'deleted' AND user_id = ? "
            "ORDER BY updated_at DESC"
        )

    def update(self, task_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        current = self.get(task_id)
        if current is None:
            raise KeyError(task_id)
        snapshot = {
            "target": changes.get("target", current["target"]),
            "source_scope": changes.get(
                "source_scope", json.loads(str(current["source_scope_json"]))
            ),
            "trigger_condition": changes.get(
                "trigger_condition", json.loads(str(current["trigger_condition_json"]))
            ),
            "frequency_seconds": int(
                changes.get("frequency_seconds", current["frequency_seconds"])
            ),
            "notification_policy": changes.get(
                "notification_policy", json.loads(str(current["notification_policy_json"]))
            ),
        }
        version = int(current["version"]) + 1
        version_id = new_id()
        now = utc_now()
        with self.store.transaction():
            self.store.execute(
                "INSERT INTO watch_task_versions VALUES (?,?,?,?,?,?,?)",
                (
                    version_id,
                    task_id,
                    self.user_id,
                    version,
                    self.user_id,
                    now,
                    json.dumps(snapshot),
                ),
            )
            cursor = self.store.execute(
                "UPDATE watch_tasks SET target=?,source_scope_json=?,trigger_condition_json=?,"
                "frequency_seconds=?,notification_policy_json=?,version=?,current_version_id=?,"
                "updated_at=? WHERE task_id=? AND user_id=?",
                (
                    snapshot["target"],
                    json.dumps(snapshot["source_scope"]),
                    json.dumps(snapshot["trigger_condition"]),
                    snapshot["frequency_seconds"],
                    json.dumps(snapshot["notification_policy"]),
                    version,
                    version_id,
                    now,
                    task_id,
                    self.user_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(task_id)
        result = self.get(task_id)
        assert result is not None
        return result

    def set_status(self, task_id: str, status: str) -> dict[str, Any]:
        cursor = self.store.execute(
            "UPDATE watch_tasks SET status=?, updated_at=? WHERE task_id=? AND user_id=?",
            (status, utc_now(), task_id, self.user_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(task_id)
        result = self.get(task_id, include_deleted=True)
        assert result is not None
        return result

    def begin_draining(self, task_id: str) -> dict[str, Any] | None:
        cursor = self.execute(
            "UPDATE watch_tasks SET status='draining', updated_at=? "
            "WHERE task_id=? AND status IN ('active','paused') AND user_id=?",
            (utc_now(), task_id),
        )
        if cursor.rowcount != 1:
            return None
        return self.get(task_id, include_deleted=True)

    def version_history(self, task_id: str) -> builtins.list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM watch_task_versions WHERE task_id=? AND user_id=? ORDER BY version",
            (task_id,),
        )
