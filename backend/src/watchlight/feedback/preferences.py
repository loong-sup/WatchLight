from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from watchlight.storage.repos.feedback import FeedbackRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.storage.store import Store


class PreferenceService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def create_from_feedback(
        self,
        user_id: str,
        task_id: str,
        feedback_id: str,
        rating: str,
        reason: str | None,
    ) -> str | None:
        if TasksRepo.for_user(self.store, user_id).get(task_id) is None:
            raise PermissionError("task does not belong to user")
        if rating == "useful" and not reason:
            return None
        if rating == "too_frequent":
            kind = "frequency_cap"
        elif rating == "useless":
            kind = "exclude"
        else:
            kind = "include"
        value: Any = 1 if kind == "frequency_cap" else (reason or "")
        preference = FeedbackRepo.for_user(self.store, user_id).insert_preference(
            {
                "task_id": task_id,
                "kind": kind,
                "value": value,
                "created_from_feedback_id": feedback_id,
            }
        )
        return str(preference["preference_id"])

    def list_for_task(self, user_id: str, task_id: str) -> list[dict[str, Any]]:
        rows = FeedbackRepo.for_user(self.store, user_id).list_preferences(task_id)
        return [
            {
                **row,
                "applies_to": task_id,
                "originating_feedback_id": row["created_from_feedback_id"],
                "value": json.loads(str(row["value_json"])),
            }
            for row in rows
        ]

    def revoke(self, user_id: str, preference_id: str) -> None:
        FeedbackRepo.for_user(self.store, user_id).revoke(preference_id)

    def apply_filter(self, user_id: str, task_id: str, text: str) -> str:
        for row in FeedbackRepo.for_user(self.store, user_id).list_preferences(task_id):
            value = str(json.loads(str(row["value_json"]))).lower()
            if row["kind"] == "exclude" and value in text.lower():
                return "exclude"
        return "include"
