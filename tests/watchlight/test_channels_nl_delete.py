from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conftest import task_fields
from watchlight.scheduler.nl import NaturalLanguageTaskFlow
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.identity import IdentityRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


def _create_task(
    store: Store, user_id: str, target: str, *, status: str = "active"
) -> dict[str, object]:
    return TasksRepo.for_user(store, user_id).create(task_fields(target=target), status=status)


def test_delete_command_lists_only_deletable_tasks(store: Store, user_id: str) -> None:
    active = _create_task(store, user_id, "Python Active")
    paused = _create_task(store, user_id, "Python Paused", status="paused")
    draining = _create_task(store, user_id, "Python Draining", status="draining")
    flow = NaturalLanguageTaskFlow(TaskService(store))

    assert flow.handle(user_id, "feishu", "如何删除任务", "dm:a") is None
    reply = flow.handle(user_id, "feishu", "删除任务", "dm:a")

    assert reply and "可删除的关注任务" in reply
    assert "Python Active" in reply and str(active["task_id"]) in reply
    assert "Python Paused" in reply and str(paused["task_id"]) in reply
    assert "Python Draining" not in reply and str(draining["task_id"]) not in reply
    assert "名称关键词" in reply and "完整任务 ID" in reply


def test_keyword_disambiguation_requires_exact_confirmation(store: Store, user_id: str) -> None:
    stable = _create_task(store, user_id, "Python Release Stable")
    security = _create_task(store, user_id, "Python Release Security")
    rust = _create_task(store, user_id, "Rust Release")
    repo = TasksRepo.for_user(store, user_id)
    flow = NaturalLanguageTaskFlow(TaskService(store))

    flow.handle(user_id, "feishu", "删除任务", "dm:a")
    narrowed = flow.handle(user_id, "feishu", "PYTHON", "dm:a")
    assert narrowed and "匹配到多个" in narrowed
    assert str(stable["task_id"]) in narrowed and str(security["task_id"]) in narrowed
    assert str(rust["task_id"]) not in narrowed
    assert repo.get(str(stable["task_id"]))["status"] == "active"  # type: ignore[index]

    outside = flow.handle(user_id, "feishu", "Rust", "dm:a")
    assert outside and "未在当前候选" in outside
    selected = flow.handle(user_id, "feishu", "security", "dm:a")
    assert selected and "请确认删除关注任务" in selected
    assert str(security["task_id"]) in selected
    assert "停止" in selected and "通知" in selected
    assert repo.get(str(security["task_id"]))["status"] == "active"  # type: ignore[index]

    for unsafe in ("确认", "确定", "删除"):
        warning = flow.handle(user_id, "feishu", unsafe, "dm:a")
        assert warning and "尚未删除" in warning
        assert repo.get(str(security["task_id"]))["status"] == "active"  # type: ignore[index]

    deleted = flow.handle(user_id, "feishu", "确认删除", "dm:a")
    assert deleted and "已进入删除流程" in deleted
    assert repo.get(str(security["task_id"]))["status"] == "draining"  # type: ignore[index]
    repeated = flow.handle(user_id, "feishu", "确认删除", "dm:a")
    assert repeated and "没有待确认删除" in repeated


@pytest.mark.parametrize("cancel", ["取消", "取消删除"])
def test_full_id_selection_can_be_cancelled(
    store: Store, user_id: str, cancel: str
) -> None:
    task = _create_task(store, user_id, "Exact ID Task")
    task_id = str(task["task_id"])
    repo = TasksRepo.for_user(store, user_id)
    flow = NaturalLanguageTaskFlow(TaskService(store))

    flow.handle(user_id, "feishu", "删除任务", "dm:a")
    sequence = flow.handle(user_id, "feishu", "1", "dm:a")
    assert sequence and "未在当前候选" in sequence
    selected = flow.handle(user_id, "feishu", task_id, "dm:a")
    assert selected and task_id in selected
    cancelled = flow.handle(user_id, "feishu", cancel, "dm:a")
    assert cancelled and "已取消删除" in cancelled
    assert repo.get(task_id)["status"] == "active"  # type: ignore[index]
    no_pending = flow.handle(user_id, "feishu", "确认删除", "dm:a")
    assert no_pending and "没有待确认删除" in no_pending
    assert repo.get(task_id)["status"] == "active"  # type: ignore[index]


def test_delete_state_expires_and_valid_selection_refreshes_ttl(
    store: Store, user_id: str
) -> None:
    expired_task = _create_task(store, user_id, "Expired Task")
    refreshed_task = _create_task(store, user_id, "Refreshed Task")
    repo = TasksRepo.for_user(store, user_id)
    flow = NaturalLanguageTaskFlow(TaskService(store))

    flow.handle(user_id, "feishu", "删除任务", "dm:expired", now=0)
    flow.handle(user_id, "feishu", "Expired", "dm:expired", now=0)
    expired = flow.handle(user_id, "feishu", "确认删除", "dm:expired", now=601)
    assert expired and "超过 10 分钟" in expired
    assert repo.get(str(expired_task["task_id"]))["status"] == "active"  # type: ignore[index]

    restarted = flow.handle(user_id, "feishu", "删除任务", "dm:expired", now=602)
    assert restarted and "可删除的关注任务" in restarted

    flow.handle(user_id, "feishu", "删除任务", "dm:refresh", now=0)
    flow.handle(user_id, "feishu", "Refreshed", "dm:refresh", now=599)
    confirmed = flow.handle(user_id, "feishu", "确认删除", "dm:refresh", now=1100)
    assert confirmed and "已进入删除流程" in confirmed
    assert repo.get(str(refreshed_task["task_id"]))["status"] == "draining"  # type: ignore[index]


def test_delete_state_is_user_and_conversation_scoped(store: Store, user_id: str) -> None:
    own = _create_task(store, user_id, "Own Task")
    other_user = str(IdentityRepo(store).create_user("Other")["user_id"])
    other = _create_task(store, other_user, "Other Secret Task")
    own_repo = TasksRepo.for_user(store, user_id)
    other_repo = TasksRepo.for_user(store, other_user)
    flow = NaturalLanguageTaskFlow(TaskService(store))

    listed = flow.handle(user_id, "feishu", "删除任务", "dm:a")
    assert listed and "Own Task" in listed and "Other Secret Task" not in listed
    foreign = flow.handle(user_id, "feishu", str(other["task_id"]), "dm:a")
    assert foreign and "未在当前候选" in foreign and "Other Secret Task" not in foreign

    flow.handle(user_id, "feishu", "Own", "dm:a")
    wrong_conversation = flow.handle(user_id, "feishu", "确认删除", "dm:b")
    assert wrong_conversation and "没有待确认删除" in wrong_conversation
    assert own_repo.get(str(own["task_id"]))["status"] == "active"  # type: ignore[index]
    assert other_repo.get(str(other["task_id"]))["status"] == "active"  # type: ignore[index]

    correct = flow.handle(user_id, "feishu", "确认删除", "dm:a")
    assert correct and "已进入删除流程" in correct
    assert own_repo.get(str(own["task_id"]))["status"] == "draining"  # type: ignore[index]


def test_confirmation_revalidates_status_and_state_is_not_persisted(
    store: Store, user_id: str
) -> None:
    task = _create_task(store, user_id, "Changing Task")
    task_id = str(task["task_id"])
    repo = TasksRepo.for_user(store, user_id)
    service = TaskService(store)
    flow = NaturalLanguageTaskFlow(service)

    flow.handle(user_id, "feishu", "删除任务", "dm:a")
    flow.handle(user_id, "feishu", "Changing", "dm:a")
    repo.set_status(task_id, "draining")
    failed = flow.handle(user_id, "feishu", "确认删除", "dm:a")
    assert failed and "状态已发生变化" in failed
    assert repo.get(task_id)["status"] == "draining"  # type: ignore[index]

    restarted_flow = NaturalLanguageTaskFlow(service)
    no_state = restarted_flow.handle(user_id, "feishu", "确认删除", "dm:a")
    assert no_state and "没有待确认删除" in no_state


def test_no_deletable_tasks_does_not_create_pending_state(store: Store, user_id: str) -> None:
    _create_task(store, user_id, "Already deleting", status="draining")
    flow = NaturalLanguageTaskFlow(TaskService(store))
    assert flow.handle(user_id, "feishu", "删除任务", "dm:a") == "当前没有可删除的关注任务。"
    reply = flow.handle(user_id, "feishu", "确认删除", "dm:a")
    assert reply and "没有待确认删除" in reply
