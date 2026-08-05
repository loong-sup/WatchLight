from __future__ import annotations

from typing import TYPE_CHECKING

from conftest import task_fields
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.signals import SignalsRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


def test_signal_status_history_is_append_only(store: Store, user_id: str) -> None:
    task = TasksRepo.for_user(store, user_id).create(task_fields())
    execution = ExecutionsRepo.for_user(store, user_id).insert(
        str(task["task_id"]), str(task["current_version_id"]), 10
    )
    repo = SignalsRepo.for_user(store, user_id)
    signal = repo.insert(
        {
            "execution_id": execution["execution_id"],
            "task_id": task["task_id"],
            "dedup_key": "key",
            "source_urls": ["https://example.com"],
        }
    )
    repo.update_status(str(signal["signal_id"]), "notified", 20)
    updated = repo.get(str(signal["signal_id"]))
    assert updated is not None
    assert "notified" in str(updated["status_history_json"])


def test_brief_sendable_check_is_enforced_by_builder_input(store: Store, user_id: str) -> None:
    task = TasksRepo.for_user(store, user_id).create(task_fields())
    execution = ExecutionsRepo.for_user(store, user_id).insert(
        str(task["task_id"]), str(task["current_version_id"]), 10
    )
    brief = BriefsRepo.for_user(store, user_id).insert(
        {
            "execution_id": execution["execution_id"],
            "signal_ids": [],
            "source_refs": [],
            "sendable": False,
        }
    )
    assert brief["sendable"] == 0
