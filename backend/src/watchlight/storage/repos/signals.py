from __future__ import annotations

import json
from typing import Any

from watchlight.storage.repos import Repo
from watchlight.storage.store import Store, new_id, utc_now


class SignalsRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> SignalsRepo:
        return cls(store, user_id)

    def insert(self, values: dict[str, Any]) -> dict[str, Any]:
        signal_id = str(values.get("signal_id") or new_id())
        at = int(values.get("captured_at", utc_now()))
        status = str(values.get("status", "proposed"))
        history = [{"status": status, "at": at}]
        self.store.execute(
            "INSERT INTO signals(signal_id,execution_id,task_id,user_id,change_ids_json,"
            "source_urls_json,captured_at,relevance,importance,novelty,source_credibility,"
            "uncertainty_level,status,dedup_key,status_history_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                signal_id,
                values["execution_id"],
                values["task_id"],
                self.user_id,
                json.dumps(values.get("change_ids", [])),
                json.dumps(values.get("source_urls", [])),
                at,
                float(values.get("relevance", 0)),
                float(values.get("importance", 0)),
                float(values.get("novelty", 0)),
                float(values.get("source_credibility", 0)),
                values.get("uncertainty_level", "medium"),
                status,
                values["dedup_key"],
                json.dumps(history),
            ),
        )
        result = self.get(signal_id)
        assert result is not None
        return result

    def get(self, signal_id: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM signals WHERE signal_id=? AND user_id=?", (signal_id,))

    def list_for_execution(self, execution_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM signals WHERE execution_id=? AND user_id=? ORDER BY captured_at",
            (execution_id,),
        )

    def list_for_task(self, task_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM signals WHERE task_id=? AND user_id=? ORDER BY captured_at DESC",
            (task_id,),
        )

    def find_recent(self, task_id: str, dedup_key: str, since: int) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM signals WHERE task_id=? AND dedup_key=? AND captured_at>=? "
            "AND status IN ('proposed','notified') AND user_id=? ORDER BY captured_at DESC LIMIT 1",
            (task_id, dedup_key, since),
        )

    def update_status(self, signal_id: str, status: str, at: int | None = None) -> None:
        current = self.get(signal_id)
        if current is None:
            raise KeyError(signal_id)
        history = json.loads(str(current["status_history_json"]))
        history.append({"status": status, "at": at or utc_now()})
        self.store.execute(
            "UPDATE signals SET status=?,status_history_json=? WHERE signal_id=? AND user_id=?",
            (status, json.dumps(history), signal_id, self.user_id),
        )
