from unittest.mock import Mock

import pytest
from watchlight.scheduler.nl import NaturalLanguageTaskFlow
from watchlight.scheduler.presentation import task_to_view
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.tasks import TasksRepo
from watchlight.storage.store import Store


def _draft(target: str, channel: str = "feishu") -> dict[str, object]:
    return {
        "target": target,
        "source_scope": {"urls": [], "keywords": [target]},
        "trigger_condition": {"must_contain": [], "must_not_contain": []},
        "frequency_seconds": 86400,
        "notification_policy": {"channels": [channel], "immediate": True},
    }


def test_two_round_natural_language_creation_requires_confirmation(
    store: Store, user_id: str
) -> None:
    flow = NaturalLanguageTaskFlow(TaskService(store))

    first = flow.handle(
        user_id,
        "feishu",
        "创建关注 https://example.com/releases 出现 v2.0 released",
    )
    assert first and "请补充" in first
    second = flow.handle(user_id, "feishu", "每天检查，通过飞书通知")
    assert second and "请确认创建" in second
    assert "**关注目标**" in second
    assert "**执行频率**：每天" in second
    assert "**通知渠道**：飞书" in second
    assert "{'target':" not in second
    assert "frequency_seconds" not in second
    task = TasksRepo.for_user(store, user_id).list()[0]
    assert task["status"] == "paused"

    final = flow.handle(user_id, "feishu", "确认")
    assert final and "已创建并启用" in final
    assert TasksRepo.for_user(store, user_id).list()[0]["status"] == "active"


def test_natural_language_flow_falls_back_after_two_incomplete_rounds(
    store: Store, user_id: str
) -> None:
    flow = NaturalLanguageTaskFlow(TaskService(store))
    assert flow.handle(user_id, "web", "创建关注 Python")
    reply = flow.handle(user_id, "web", "还没想好")
    assert reply and "任务表单" in reply
    assert TasksRepo.for_user(store, user_id).list() == []


@pytest.mark.parametrize(
    "message",
    ["目前创建了哪些任务", "查看已创建任务", "我之前创建的任务还在吗"],
)
def test_task_list_intents_return_persisted_tasks(
    store: Store, user_id: str, message: str
) -> None:
    service = TaskService(store)
    for target in ("主流开源大模型的重要发布", "Python 安全更新"):
        created = service.create(user_id, _draft(target))
        assert created.task_id and created.normalized_version_id
        service.confirm(user_id, created.task_id, created.normalized_version_id, now=100)

    reply = NaturalLanguageTaskFlow(service).handle(user_id, "feishu", message)

    assert reply and "当前关注任务（2）" in reply
    assert reply.count("主流开源大模型的重要发布") == 1
    assert reply.count("Python 安全更新") == 1
    assert "已启用（active）" in reply
    assert "执行频率：每天" in reply
    assert "通知渠道：飞书" in reply


def test_task_list_empty_and_query_failure_are_distinct(store: Store, user_id: str) -> None:
    service = TaskService(store)
    flow = NaturalLanguageTaskFlow(service)
    assert flow.handle(user_id, "feishu", "当前有哪些任务") == "当前没有关注任务。"

    service.list = Mock(side_effect=RuntimeError("database unavailable"))  # type: ignore[method-assign]
    reply = flow.handle(user_id, "feishu", "当前有哪些任务")
    assert reply and "暂时无法查询" in reply
    assert "没有关注任务" not in reply


def test_create_intent_is_not_misclassified_as_list(store: Store, user_id: str) -> None:
    reply = NaturalLanguageTaskFlow(TaskService(store)).handle(
        user_id, "feishu", "创建关注 Python 发布"
    )
    assert reply and "请补充" in reply


def test_invalid_notification_policy_is_safely_presented() -> None:
    view = task_to_view(
        {
            "task_id": "task-1",
            "target": "Target",
            "status": "active",
            "frequency_seconds": 3600,
            "notification_policy_json": "{not-json",
        }
    )
    assert view["notification_channels"] == []
    assert view["notification_channel_labels"] == []
