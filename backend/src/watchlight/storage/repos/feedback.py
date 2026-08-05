from __future__ import annotations

import json
from typing import Any

from watchlight.storage.repos import Repo
from watchlight.storage.store import Store, new_id, utc_now


class FeedbackRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> FeedbackRepo:
        return cls(store, user_id)

    def insert_feedback(self, values: dict[str, Any]) -> dict[str, Any]:
        feedback_id = str(values.get("feedback_id") or new_id())
        self.store.execute(
            "INSERT INTO feedbacks(feedback_id,delivery_id,user_id,rating,reason,created_at,"
            "applied_preference_id) VALUES (?,?,?,?,?,?,?)",
            (
                feedback_id,
                values["delivery_id"],
                self.user_id,
                values["rating"],
                values.get("reason"),
                values.get("created_at", utc_now()),
                values.get("applied_preference_id"),
            ),
        )
        result = self.one(
            "SELECT * FROM feedbacks WHERE feedback_id=? AND user_id=?", (feedback_id,)
        )
        assert result is not None
        return result

    def link_preference(self, feedback_id: str, preference_id: str) -> None:
        self.store.execute(
            "UPDATE feedbacks SET applied_preference_id=? WHERE feedback_id=? AND user_id=?",
            (preference_id, feedback_id, self.user_id),
        )

    def insert_preference(self, values: dict[str, Any]) -> dict[str, Any]:
        preference_id = str(values.get("preference_id") or new_id())
        self.store.execute(
            "INSERT INTO preferences(preference_id,user_id,task_id,scope,kind,value_json,"
            "created_from_feedback_id,created_at,revoked_at) VALUES (?,?,?,?,?,?,?,?,NULL)",
            (
                preference_id,
                self.user_id,
                values["task_id"],
                values.get("scope", "task"),
                values["kind"],
                json.dumps(values.get("value"), ensure_ascii=False),
                values.get("created_from_feedback_id"),
                values.get("created_at", utc_now()),
            ),
        )
        result = self.one(
            "SELECT * FROM preferences WHERE preference_id=? AND user_id=?", (preference_id,)
        )
        assert result is not None
        return result

    def list_preferences(self, task_id: str, *, active_only: bool = True) -> list[dict[str, Any]]:
        clause = " AND revoked_at IS NULL" if active_only else ""
        return self.all(
            f"SELECT * FROM preferences WHERE task_id=? AND user_id=?{clause} ORDER BY created_at",
            (task_id,),
        )

    def revoke(self, preference_id: str, at: int | None = None) -> None:
        cursor = self.store.execute(
            "UPDATE preferences SET revoked_at=? WHERE preference_id=? AND user_id=?",
            (at or utc_now(), preference_id, self.user_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(preference_id)

    def list_feedback(self) -> list[dict[str, Any]]:
        return self.all("SELECT * FROM feedbacks WHERE user_id=? ORDER BY created_at")
