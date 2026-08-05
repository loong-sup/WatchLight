from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING

from watchlight.agents.runtime.embedded.runner import EmbeddedRuntime
from watchlight.contracts.agent.runtime import AgentEventType, AgentRunRequest
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.identity import IdentityRepo
from watchlight.tools.builtin.watch_tasks import create_watch_tasks_list_tool
from watchlight.tools.execution import execute_tool
from watchlight.tools.policy import ToolPolicy
from watchlight.tools.registry import ToolRegistry
from watchlight.tools.types import ToolContext

if TYPE_CHECKING:
    from watchlight.storage.store import Store


def _draft(target: str) -> dict[str, object]:
    return {
        "target": target,
        "source_scope": {"urls": [], "keywords": [target]},
        "trigger_condition": {"must_contain": [], "must_not_contain": []},
        "frequency_seconds": 86400,
        "notification_policy": {"channels": ["feishu"], "immediate": True},
    }


async def test_watch_tasks_tool_uses_only_context_identity(store: Store, user_id: str) -> None:
    other_user = str(IdentityRepo(store).create_user("Other")["user_id"])
    service = TaskService(store)
    service.create(user_id, _draft("User A task"))
    service.create(other_user, _draft("User B task"))
    tool = create_watch_tasks_list_tool(store)
    before_tasks = [dict(row) for row in store.fetchall("SELECT * FROM watch_tasks")]
    before_versions = [dict(row) for row in store.fetchall("SELECT * FROM watch_task_versions")]
    before_executions = [dict(row) for row in store.fetchall("SELECT * FROM executions")]

    assert "user_id" not in tool.input_schema["properties"]
    assert tool.input_schema["additionalProperties"] is False
    assert tool.handler is not None
    result = await tool.handler(
        {"user_id": other_user},
        ToolContext(user_id=user_id),
    )

    assert result["count"] == 1
    assert result["tasks"][0]["target"] == "User A task"
    assert set(result["tasks"][0]) == {
        "task_id",
        "target",
        "status",
        "status_label",
        "frequency_seconds",
        "frequency_label",
        "notification_channels",
        "notification_channel_labels",
    }
    assert [dict(row) for row in store.fetchall("SELECT * FROM watch_tasks")] == before_tasks
    assert [dict(row) for row in store.fetchall("SELECT * FROM watch_task_versions")] == (
        before_versions
    )
    assert [dict(row) for row in store.fetchall("SELECT * FROM executions")] == before_executions


async def test_watch_tasks_tool_fails_closed_without_identity(store: Store) -> None:
    registry = ToolRegistry()
    registry.register(create_watch_tasks_list_tool(store))

    result = await execute_tool(
        registry,
        ToolPolicy(profile="messaging"),
        "watch_tasks_list",
        {},
        ToolContext(),
    )

    assert result.success is False
    assert result.error and "identity is required" in result.error


async def test_embedded_runtime_injects_authenticated_user_into_task_tool(
    store: Store, user_id: str
) -> None:
    TaskService(store).create(user_id, _draft("Authenticated task"))
    tool_registry = ToolRegistry()
    tool_registry.register(create_watch_tasks_list_tool(store))

    class FakeProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def create_stream(self, **kwargs: object):
            self.calls += 1
            if self.calls == 1:
                yield {
                    "type": "tool_call",
                    "id": "call-1",
                    "name": "watch_tasks_list",
                    "params": {},
                }
                return
            messages = kwargs["messages"]
            assert isinstance(messages, list)
            assert any("Authenticated task" in str(message) for message in messages)
            yield {"type": "text_delta", "text": "已找到真实任务"}

    provider = FakeProvider()
    runtime = EmbeddedRuntime(
        provider_registry=SimpleNamespace(get=lambda _provider_id: provider),
        tool_registry=tool_registry,
    )
    request = AgentRunRequest(
        run_id="run-1",
        session_key="dm:feishu:user",
        provider_id="fake",
        model_id="fake-model",
        system_prompt="test",
        user_message="给我回顾一下我设定的追踪安排",
        metadata={"toolProfile": "messaging", "userId": user_id},
    )

    events = [event async for event in runtime.run(request, asyncio.Event())]

    tool_results = [event for event in events if event.type == AgentEventType.TOOL_CALL_RESULT]
    assert len(tool_results) == 1
    assert "Authenticated task" in str(tool_results[0].tool_result)
    assert any(event.text == "已找到真实任务" for event in events)
