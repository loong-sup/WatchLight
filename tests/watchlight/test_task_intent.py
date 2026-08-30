from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from watchlight.scheduler.intent import (
    ModelTaskIntentExtractor,
    deterministic_intent,
    sanitize_patch,
)
from watchlight.scheduler.nl import NaturalLanguageTaskFlow
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from watchlight.storage import Store


def test_deterministic_intent_extracts_concise_target_and_five_hour_interval() -> None:
    result = deterministic_intent(
        "请创建一个任务帮我关注小米公司的澎程汽车，每隔5小时向我汇报一次，"
        "请使用飞书通知我"
    )

    assert result.intent == "create"
    assert result.patch == {
        "target": "小米公司的澎程汽车",
        "source_scope": {"urls": [], "keywords": ["小米公司的澎程汽车"]},
        "trigger_condition": {"must_contain": [], "must_not_contain": []},
        "frequency_seconds": 18000,
        "notification_policy": {
            "channels": ["feishu"],
            "immediate": True,
            "report_on_no_change": True,
        },
    }


def test_negated_frequency_correction_uses_last_positive_value() -> None:
    result = deterministic_intent(
        "不是每五小时，是每天",
        {"target": "小米汽车", "frequency_seconds": 18000},
    )

    assert result.intent == "update"
    assert result.patch == {"frequency_seconds": 86400}


def test_fixed_clock_schedule_requires_clarification() -> None:
    result = deterministic_intent("创建关注 Python 发布，每天上午10点飞书通知")

    assert result.clarification
    assert "暂不支持固定钟点" in result.clarification


def test_patch_sanitizer_drops_unknown_fields_and_invalid_types() -> None:
    patch = sanitize_patch(
        {
            "target": " Python 发布 ",
            "frequency_seconds": "3600",
            "execute_shell": "rm -rf /",
            "notification_policy": {"channels": ["feishu", "unknown"]},
        }
    )

    assert patch == {
        "target": "Python 发布",
        "notification_policy": {"channels": ["feishu"], "immediate": True},
    }


def test_correction_updates_same_paused_task_then_confirms(
    store: Store, user_id: str
) -> None:
    flow = NaturalLanguageTaskFlow(TaskService(store))

    first = flow.handle(
        user_id,
        "feishu",
        "请创建一个任务帮我关注小米公司的澎程汽车，每隔5小时向我汇报一次，"
        "请使用飞书通知我",
    )
    assert first and "每 5 小时" in first
    assert "**关注目标**：小米公司的澎程汽车" in first
    assert "请创建一个任务" not in first

    correction = flow.handle(user_id, "feishu", "不是每五小时，是每天")
    assert correction and "**执行频率**：每天" in correction
    assert "每隔5小时" not in correction

    tasks = TasksRepo.for_user(store, user_id).list()
    assert len(tasks) == 1
    assert tasks[0]["status"] == "paused"
    assert tasks[0]["frequency_seconds"] == 86400
    assert tasks[0]["target"] == "小米公司的澎程汽车"
    assert tasks[0]["version"] == 2

    confirmed = flow.handle(user_id, "feishu", "确认")
    assert confirmed == "关注任务已创建并启用：小米公司的澎程汽车"
    assert TasksRepo.for_user(store, user_id).list()[0]["status"] == "active"


def test_full_restatement_updates_target_source_and_frequency_without_duplicate(
    store: Store, user_id: str
) -> None:
    flow = NaturalLanguageTaskFlow(TaskService(store))
    flow.handle(user_id, "feishu", "创建关注旧名称，每隔5小时，通过飞书通知")

    reply = flow.handle(
        user_id,
        "feishu",
        "请创建一个任务帮我关注小米汽车，每天向我汇报，请使用飞书通知我",
    )

    assert reply and "**关注目标**：小米汽车" in reply
    tasks = TasksRepo.for_user(store, user_id).list()
    assert len(tasks) == 1
    assert tasks[0]["target"] == "小米汽车"
    assert json.loads(str(tasks[0]["source_scope_json"]))["keywords"] == ["小米汽车"]
    assert tasks[0]["frequency_seconds"] == 86400


class FakeProvider:
    def __init__(self, response: str) -> None:
        self.response = response

    async def create_stream(
        self, _model: str, _messages: list[dict[str, Any]], **_kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "text_delta", "text": self.response}


@pytest.mark.asyncio
async def test_model_extractor_accepts_only_sanitized_json_patch() -> None:
    provider = FakeProvider(
        "```json\n"
        '{"intent":"update","patch":{"target":"小米汽车",'
        '"frequency_seconds":86400,"dangerous":true},"confidence":0.9}'
        "\n```"
    )
    result = await ModelTaskIntentExtractor(provider, "test-model").extract(
        "改成每天", {"target": "旧值"}
    )

    assert result is not None
    assert result.intent == "update"
    assert result.patch == {"target": "小米汽车", "frequency_seconds": 86400}


@pytest.mark.asyncio
async def test_model_extractor_rejects_invalid_json() -> None:
    result = await ModelTaskIntentExtractor(
        FakeProvider("这不是 JSON"), "test-model"
    ).extract("创建任务", None)

    assert result is None
