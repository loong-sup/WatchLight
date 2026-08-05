from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from watchlight.storage.repos.feedback import FeedbackRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.observing.redact import Redactor
    from watchlight.storage.store import Store


def export_user_data(store: Store, user_id: str, redactor: Redactor) -> dict[str, Any]:
    tasks = TasksRepo.for_user(store, user_id)
    payload = {
        "tasks": [
            {**task, "versions": tasks.version_history(str(task["task_id"]))}
            for task in tasks.list()
        ],
        "feedback": FeedbackRepo.for_user(store, user_id).list_feedback(),
        "preferences": [
            item
            for task in tasks.list()
            for item in FeedbackRepo.for_user(store, user_id).list_preferences(
                str(task["task_id"]), active_only=False
            )
        ],
    }
    return cast("dict[str, Any]", redactor.redact(payload))
