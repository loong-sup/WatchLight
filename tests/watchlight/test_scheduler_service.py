from __future__ import annotations

from typing import TYPE_CHECKING

from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


def complete_draft(**changes: object) -> dict[str, object]:
    draft: dict[str, object] = {
        "target": "Watch releases",
        "source_scope": {"urls": ["https://example.com"]},
        "trigger_condition": {"must_contain": ["release"]},
        "frequency_seconds": 3600,
        "notification_policy": {"channels": ["web"], "immediate": True},
    }
    draft.update(changes)
    return draft


def test_missing_fields_do_not_write_task(store: Store, user_id: str) -> None:
    service = TaskService(store)
    result = service.create(user_id, {"target": "Watch releases"})
    assert "frequency_seconds" in result.missing_fields
    assert TasksRepo.for_user(store, user_id).list() == []


def test_confirm_activates_and_schedules(store: Store, user_id: str) -> None:
    service = TaskService(store)
    created = service.create(user_id, complete_draft())
    assert created.task_id and created.normalized_version_id
    assert TasksRepo.for_user(store, user_id).get(created.task_id)["status"] == "paused"  # type: ignore[index]
    confirmed = service.confirm(
        user_id, created.task_id, created.normalized_version_id, now=100
    )
    assert confirmed["status"] == "active"
    executions = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)
    assert executions[0]["scheduled_at"] == 3700


def test_frequency_bounds_and_unsupported_actions(store: Store, user_id: str) -> None:
    service = TaskService(store)
    assert service.create(user_id, complete_draft(frequency_seconds=60)).error == (
        "frequency_out_of_range"
    )
    assert service.create(user_id, "替我支付并每天通知飞书").error == (
        "unsupported_action:支付"
    )


def test_update_versions_and_manual_trigger_preserves_schedule(
    store: Store, user_id: str
) -> None:
    service = TaskService(store)
    created = service.create(user_id, complete_draft())
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=100)
    before = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)
    service.update(user_id, created.task_id, {"target": "Watch major releases"})
    manual_id = service.trigger_now(user_id, created.task_id, now=200)
    after = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)
    assert any(row["execution_id"] == manual_id for row in after)
    assert any(row["scheduled_at"] == before[0]["scheduled_at"] for row in after)
