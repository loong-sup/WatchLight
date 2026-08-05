from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from watchlight.contracts.channel.plugin import InboundMessage
from watchlight.gateway.boot import AgentRunResult, GatewayRuntime
from watchlight.identity import IdentityRegistry
from watchlight.scheduler.loop import SchedulerLoop
from watchlight.scheduler.nl import NaturalLanguageTaskFlow
from watchlight.scheduler.service import TaskService
from watchlight.sessions.store import SessionStore
from watchlight.sessions.transcript import TranscriptManager
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage import Store


def _user_count(store: Store) -> int:
    row = store.fetchone("SELECT COUNT(*) AS count FROM users")
    return int(row["count"] if row else 0)


def test_first_feishu_message_registers_independent_identity(store: Store) -> None:
    registry = IdentityRegistry(store)
    before = _user_count(store)

    resolved = registry.resolve_or_register(
        "feishu", "ou-new", display_name="Feishu User", timezone="Asia/Shanghai"
    )

    assert resolved.status == "bound"
    assert resolved.user_id is not None
    assert _user_count(store) == before + 1
    identity = registry.repo.find_channel_identity("feishu", "ou-new")
    assert identity and identity["status"] == "bound"


def test_pending_and_unbound_identity_are_never_auto_registered(store: Store) -> None:
    registry = IdentityRegistry(store)
    primary = registry.register("web", "owner")
    registry.start_binding(primary, "feishu", "ou-pending")
    count_after_pending = _user_count(store)

    pending = registry.resolve_or_register("feishu", "ou-pending")
    assert pending.status == "pending"
    assert pending.user_id is None
    assert _user_count(store) == count_after_pending

    token = registry.start_binding(primary, "feishu", "ou-bound")
    registry.confirm_binding(token, "web")
    unbind_token, _ = registry.start_unbind(primary, "feishu")
    registry.confirm_unbind(unbind_token, "web")
    count_after_unbind = _user_count(store)

    unbound = registry.resolve_or_register("feishu", "ou-bound")
    assert unbound.status == "unbinding"
    assert unbound.user_id is None
    assert _user_count(store) == count_after_unbind


@pytest.mark.asyncio
async def test_first_feishu_message_continues_to_original_agent_flow(store: Store) -> None:
    registry = IdentityRegistry(store)
    result = AgentRunResult()
    result.texts.append("正常回复")
    sent: list[str] = []

    class FakeChannel:
        async def send(self, account_id: str, conversation_id: str, message: object) -> None:
            sent.append(str(getattr(message, "text", "")))

    runtime = object.__new__(GatewayRuntime)
    runtime.watchlight_mvp = SimpleNamespace(
        identity=registry,
        nl_tasks=SimpleNamespace(handle=lambda *_args, **_kwargs: None),
    )
    runtime.session_store = SimpleNamespace(update=Mock())
    runtime._emit_runtime_event = AsyncMock()
    runtime.run_agent_for_session = AsyncMock(return_value=result)
    runtime.channel_registry = SimpleNamespace(get=lambda _channel: FakeChannel())
    message = InboundMessage(
        channel="feishu",
        accountId="default",
        senderId="ou-first-chat",
        conversationId="oc-chat",
        text="你好",
        raw={"message_id": "om-1"},
    )

    await GatewayRuntime._handle_inbound(runtime, message)

    runtime.run_agent_for_session.assert_awaited_once()
    assert runtime.run_agent_for_session.await_args.kwargs["user_id"] == registry.resolve(
        "feishu", "ou-first-chat"
    ).user_id
    assert registry.resolve("feishu", "ou-first-chat").status == "bound"
    assert sent == ["正常回复"]


@pytest.mark.asyncio
async def test_feishu_task_flow_persists_transcript_and_lists_real_task(
    store: Store, tmp_path: Path
) -> None:
    registry = IdentityRegistry(store)
    service = TaskService(store)
    sent: list[str] = []

    class FakeChannel:
        async def send(self, account_id: str, conversation_id: str, message: object) -> None:
            sent.append(str(getattr(message, "text", "")))

    runtime = object.__new__(GatewayRuntime)
    runtime.watchlight_mvp = SimpleNamespace(
        identity=registry,
        nl_tasks=NaturalLanguageTaskFlow(service),
    )
    runtime.session_store = SessionStore(tmp_path)
    runtime.transcript_manager = TranscriptManager(tmp_path)
    runtime._emit_runtime_event = AsyncMock()
    runtime.run_agent_for_session = AsyncMock()
    runtime.channel_registry = SimpleNamespace(get=lambda _channel: FakeChannel())

    async def inbound(text: str, message_id: str) -> None:
        await GatewayRuntime._handle_inbound(
            runtime,
            InboundMessage(
                channel="feishu",
                accountId="default",
                senderId="ou-task-chat",
                conversationId="oc-chat",
                text=text,
                raw={"message_id": message_id},
            ),
        )

    await inbound("创建关注主流开源大模型的重要发布，每天通过飞书通知", "om-1")
    await inbound("确认", "om-2")
    await inbound("目前创建了哪些任务", "om-3")

    runtime.run_agent_for_session.assert_not_awaited()
    assert "请确认创建关注任务" in sent[0]
    assert "已创建并启用" in sent[1]
    assert "当前关注任务（1）" in sent[2]
    assert "已启用（active）" in sent[2]
    assert "执行频率：每天" in sent[2]
    assert "通知渠道：飞书" in sent[2]

    entry = runtime.session_store.get("dm:feishu:ou-task-chat")
    assert entry is not None
    transcript = runtime.transcript_manager.read_raw(entry.session_id)
    assert [line["role"] for line in transcript] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert [line["content"] for line in transcript[::2]] == [
        "创建关注主流开源大模型的重要发布，每天通过飞书通知",
        "确认",
        "目前创建了哪些任务",
    ]


@pytest.mark.asyncio
async def test_feishu_keyword_delete_flow_persists_and_converges(
    store: Store, tmp_path: Path
) -> None:
    registry = IdentityRegistry(store)
    user_id = registry.register("feishu", "ou-delete-chat")
    service = TaskService(store)

    def create_active(target: str) -> str:
        created = service.create(
            user_id,
            {
                "target": target,
                "source_scope": {"urls": [], "keywords": [target]},
                "trigger_condition": {"must_contain": [], "must_not_contain": []},
                "frequency_seconds": 86400,
                "notification_policy": {"channels": ["feishu"], "immediate": True},
            },
        )
        assert created.task_id and created.normalized_version_id
        service.confirm(user_id, created.task_id, created.normalized_version_id, now=100)
        return created.task_id

    release_id = create_active("开源模型重要发布")
    security_id = create_active("开源模型安全更新")
    sent: list[str] = []

    class FakeChannel:
        async def send(self, account_id: str, conversation_id: str, message: object) -> None:
            sent.append(str(getattr(message, "text", "")))

    runtime = object.__new__(GatewayRuntime)
    runtime.watchlight_mvp = SimpleNamespace(
        identity=registry,
        nl_tasks=NaturalLanguageTaskFlow(service),
    )
    runtime.session_store = SessionStore(tmp_path)
    runtime.transcript_manager = TranscriptManager(tmp_path)
    runtime._emit_runtime_event = AsyncMock()
    runtime.run_agent_for_session = AsyncMock()
    runtime.channel_registry = SimpleNamespace(get=lambda _channel: FakeChannel())

    async def inbound(text: str, message_id: str) -> None:
        await GatewayRuntime._handle_inbound(
            runtime,
            InboundMessage(
                channel="feishu",
                accountId="default",
                senderId="ou-delete-chat",
                conversationId="oc-delete",
                text=text,
                raw={"message_id": message_id},
            ),
        )

    await inbound("删除任务", "om-delete-1")
    await inbound("开源模型", "om-delete-2")
    await inbound("安全", "om-delete-3")
    await inbound("确认删除", "om-delete-4")

    runtime.run_agent_for_session.assert_not_awaited()
    assert "可删除的关注任务" in sent[0]
    assert "匹配到多个" in sent[1]
    assert "请确认删除关注任务" in sent[2] and security_id in sent[2]
    assert "已进入删除流程" in sent[3]
    repo = TasksRepo.for_user(store, user_id)
    assert repo.get(security_id)["status"] == "draining"  # type: ignore[index]
    assert repo.get(release_id)["status"] == "active"  # type: ignore[index]

    entry = runtime.session_store.get("dm:feishu:ou-delete-chat")
    assert entry is not None
    transcript = runtime.transcript_manager.read_raw(entry.session_id)
    assert [line["role"] for line in transcript] == ["user", "assistant"] * 4
    assert [line["content"] for line in transcript[::2]] == [
        "删除任务",
        "开源模型",
        "安全",
        "确认删除",
    ]

    await SchedulerLoop(store).tick(now=101)
    assert repo.get(security_id) is None
    assert repo.get(security_id, include_deleted=True)["status"] == "deleted"  # type: ignore[index]
    security_executions = ExecutionsRepo.for_user(store, user_id).list_for_task(security_id)
    assert [row["status"] for row in security_executions] == ["cancelled"]
    assert repo.get(release_id)["status"] == "active"  # type: ignore[index]
