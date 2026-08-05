from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from watchlight.channels.feishu.message import parse_inbound
from watchlight.channels.routing import resolve_session_key
from watchlight.contracts.channel.plugin import InboundMessage
from watchlight.gateway.boot import GatewayRuntime
from watchlight.identity import IdentityRegistry
from watchlight.scheduler.nl import NaturalLanguageTaskFlow
from watchlight.scheduler.service import TaskService
from watchlight.sessions.store import SessionStore
from watchlight.sessions.transcript import TranscriptManager

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage import Store


def _group_message(sender_id: str, conversation_id: str = "oc-group") -> InboundMessage:
    return InboundMessage(
        channel="feishu",
        accountId="default",
        senderId=sender_id,
        conversationId=conversation_id,
        text="你好",
        chatType="group",
    )


def test_group_session_key_is_scoped_by_group_and_sender() -> None:
    user_a = resolve_session_key(_group_message("ou-a"))
    user_b = resolve_session_key(_group_message("ou-b"))
    other_group = resolve_session_key(_group_message("ou-a", "oc-other"))

    assert user_a == "group:feishu:oc-group:ou-a"
    assert user_b == "group:feishu:oc-group:ou-b"
    assert other_group == "group:feishu:oc-other:ou-a"
    assert len({user_a, user_b, other_group}) == 3


def test_direct_message_session_key_is_unchanged() -> None:
    message = InboundMessage(
        channel="feishu",
        accountId="default",
        senderId="ou-a",
        conversationId="oc-dm",
        text="你好",
        chatType="dm",
    )

    assert resolve_session_key(message) == "dm:feishu:ou-a"


def test_parse_group_message_removes_bot_mention_and_keeps_human_mention() -> None:
    event = {
        "event": {
            "sender": {"sender_id": {"open_id": "ou-sender"}},
            "message": {
                "message_id": "om-1",
                "chat_id": "oc-group",
                "chat_type": "group",
                "message_type": "text",
                "content": json.dumps(
                    {"text": "@_user_1 grey 是 @_user_2"}, ensure_ascii=False
                ),
                "mentions": [
                    {
                        "key": "@_user_1",
                        "id": {"open_id": "ou-bot"},
                        "name": "Watchlight",
                    },
                    {
                        "key": "@_user_2",
                        "id": {"open_id": "ou-grey"},
                        "name": "Grey",
                    },
                ],
            },
        }
    }

    message = parse_inbound(event, bot_open_id="ou-bot")

    assert message is not None
    assert message.text == "grey 是 @Grey"
    assert message.sender_id == "ou-sender"
    assert message.chat_type == "group"
    assert message.raw and message.raw["mentioned_bot"] is True


def test_parse_group_message_does_not_treat_human_only_mention_as_bot() -> None:
    event = {
        "event": {
            "sender": {"sender_id": {"open_id": "ou-sender"}},
            "message": {
                "chat_id": "oc-group",
                "chat_type": "group",
                "message_type": "text",
                "content": json.dumps({"text": "你好 @_user_1"}, ensure_ascii=False),
                "mentions": [
                    {
                        "key": "@_user_1",
                        "id": {"open_id": "ou-human"},
                        "name": "Human",
                    }
                ],
            },
        }
    }

    message = parse_inbound(event, bot_open_id="ou-bot")

    assert message is not None
    assert message.text == "你好 @Human"
    assert message.raw and message.raw["mentioned_bot"] is False


@pytest.mark.asyncio
async def test_same_group_users_have_isolated_transcripts_and_original_reply_target(
    store: Store, tmp_path: Path
) -> None:
    registry = IdentityRegistry(store)
    service = TaskService(store)
    sent_to: list[str] = []

    class FakeChannel:
        async def send(self, _account_id: str, conversation_id: str, _message: object) -> None:
            sent_to.append(conversation_id)

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

    async def inbound(sender_id: str, text: str, message_id: str) -> None:
        await GatewayRuntime._handle_inbound(
            runtime,
            InboundMessage(
                channel="feishu",
                accountId="default",
                senderId=sender_id,
                conversationId="oc-shared",
                text=text,
                chatType="group",
                raw={"message_id": message_id},
            ),
        )

    await inbound("ou-a", "当前创建了哪些任务", "om-a-1")
    await inbound("ou-b", "删除任务", "om-b-1")
    await inbound("ou-a", "当前有哪些任务", "om-a-2")

    key_a = "group:feishu:oc-shared:ou-a"
    key_b = "group:feishu:oc-shared:ou-b"
    entry_a = runtime.session_store.get(key_a)
    entry_b = runtime.session_store.get(key_b)
    assert entry_a is not None and entry_b is not None
    assert entry_a.session_id != entry_b.session_id

    transcript_a = runtime.transcript_manager.read_raw(entry_a.session_id)
    transcript_b = runtime.transcript_manager.read_raw(entry_b.session_id)
    user_lines_a = [line for line in transcript_a if line["role"] == "user"]
    user_lines_b = [line for line in transcript_b if line["role"] == "user"]

    assert [line["content"] for line in user_lines_a] == [
        "当前创建了哪些任务",
        "当前有哪些任务",
    ]
    assert [line["content"] for line in user_lines_b] == ["删除任务"]
    assert {line["senderId"] for line in user_lines_a} == {"ou-a"}
    assert {line["senderId"] for line in user_lines_b} == {"ou-b"}
    assert all(line.get("userId") for line in [*user_lines_a, *user_lines_b])
    assert sent_to == ["oc-shared", "oc-shared", "oc-shared"]
