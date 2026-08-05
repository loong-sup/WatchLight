from __future__ import annotations

import json
from typing import Any

from watchlight.storage.repos import Repo
from watchlight.storage.store import Store, new_id, utc_now


class EventsRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> EventsRepo:
        return cls(store, user_id)

    def insert(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = str(event.get("event_id") or new_id())
        self.store.execute(
            "INSERT INTO events(event_id,execution_id,task_id,user_id,event_type,stage,"
            "payload_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                event_id,
                event.get("execution_id"),
                event.get("task_id"),
                self.user_id,
                event["event_type"],
                event["stage"],
                json.dumps(event.get("payload", {}), ensure_ascii=False),
                event.get("created_at", utc_now()),
            ),
        )
        result = self.one("SELECT * FROM events WHERE event_id=? AND user_id=?", (event_id,))
        assert result is not None
        return result

    def list_by_execution(self, execution_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM events WHERE execution_id=? AND user_id=? ORDER BY created_at",
            (execution_id,),
        )
