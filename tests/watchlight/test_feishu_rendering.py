from __future__ import annotations

import json
from typing import Any

import pytest
import watchlight.channels.feishu.auth as feishu_auth_module
from watchlight.channels.feishu.auth import FEISHU_TOKEN_URL, FeishuAuth
from watchlight.channels.feishu.client import (
    FEISHU_MESSAGE_URL,
    FeishuClient,
    build_markdown_card,
)
from watchlight.channels.feishu.message import (
    markdown_to_feishu_markdown,
    markdown_to_plain_text,
)
from watchlight.channels.feishu.plugin import FeishuChannelPlugin
from watchlight.contracts.channel.plugin import OutboundMessage


def test_markdown_card_uses_feishu_markdown_element() -> None:
    text = "## 标题\n\n**重点**\n- [来源](https://example.com) 和 `任务 ID`"
    card = build_markdown_card(text)

    assert card["config"]["wide_screen_mode"] is True
    assert card["elements"] == [
        {
            "tag": "markdown",
            "content": (
                "**标题**\n\n**重点**\n- [来源](https://example.com) 和 任务 ID"
            ),
        }
    ]


def test_feishu_markdown_converts_all_heading_levels_and_code_markers() -> None:
    rendered = markdown_to_feishu_markdown(
        "# 一级\n### 三级\n\n```text\n任务 `019fc`\n```"
    )

    assert rendered == "**一级**\n**三级**\n\n任务 019fc\n"
    assert "#" not in rendered
    assert "`" not in rendered


def test_plain_text_fallback_removes_markdown_source() -> None:
    rendered = markdown_to_plain_text(
        "## 标题\n\n**重点**：[来源](https://example.com) 和 `代码`"
    )

    assert rendered == "标题\n\n重点：来源（https://example.com） 和 代码"


@pytest.mark.asyncio
async def test_feishu_auth_retries_invalid_json_response(httpx_mock, monkeypatch) -> None:
    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(feishu_auth_module, "MAX_RETRY", 2)
    monkeypatch.setattr(feishu_auth_module.asyncio, "sleep", no_sleep)
    httpx_mock.add_response(method="POST", url=FEISHU_TOKEN_URL, text="")
    httpx_mock.add_response(
        method="POST",
        url=FEISHU_TOKEN_URL,
        json={"code": 0, "tenant_access_token": "token", "expire": 7200},
    )

    assert await FeishuAuth("app-id", "secret").get_token() == "token"


@pytest.mark.asyncio
async def test_feishu_client_sends_user_notification_with_open_id(httpx_mock) -> None:
    class FakeAuth:
        async def get_token(self) -> str:
            return "tenant-token"

    httpx_mock.add_response(
        method="POST",
        url=f"{FEISHU_MESSAGE_URL}?receive_id_type=open_id",
        json={"code": 0, "msg": "success"},
    )
    client = FeishuClient(FakeAuth())  # type: ignore[arg-type]

    result = await client.send_markdown(
        "ou-user", "**定时通知**", receive_id_type="open_id"
    )

    assert result["code"] == 0
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == "Bearer tenant-token"
    body = json.loads(request.content)
    assert body["receive_id"] == "ou-user"
    assert body["msg_type"] == "interactive"


@pytest.mark.asyncio
async def test_feishu_client_reports_http_failure(httpx_mock) -> None:
    class FakeAuth:
        async def get_token(self) -> str:
            return "tenant-token"

    httpx_mock.add_response(
        method="POST",
        url=f"{FEISHU_MESSAGE_URL}?receive_id_type=open_id",
        status_code=500,
    )
    client = FeishuClient(FakeAuth())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="Feishu send failed: HTTP 500"):
        await client.send_text("ou-user", "通知", receive_id_type="open_id")


@pytest.mark.asyncio
async def test_plugin_prefers_markdown_card() -> None:
    calls: list[str] = []
    receive_types: list[str] = []

    class FakeClient:
        async def send_markdown(
            self, _chat: str, _text: str, receive_id_type: str = "chat_id"
        ) -> dict[str, Any]:
            calls.append("markdown")
            receive_types.append(receive_id_type)
            return {"code": 0}

        async def send_text(
            self, _chat: str, _text: str, receive_id_type: str = "chat_id"
        ) -> dict[str, Any]:
            calls.append("text")
            return {"code": 0}

    plugin = FeishuChannelPlugin()
    plugin._clients["default"] = FakeClient()  # type: ignore[assignment]
    await plugin.send("default", "oc-chat", OutboundMessage(text="**已完成**"))

    assert calls == ["markdown"]
    assert receive_types == ["chat_id"]


@pytest.mark.asyncio
async def test_plugin_uses_open_id_for_scheduled_notification() -> None:
    targets: list[tuple[str, str]] = []

    class FakeClient:
        async def send_markdown(
            self, receive_id: str, _text: str, receive_id_type: str = "chat_id"
        ) -> dict[str, Any]:
            targets.append((receive_id, receive_id_type))
            return {"code": 0}

    plugin = FeishuChannelPlugin()
    plugin._clients["default"] = FakeClient()  # type: ignore[assignment]
    await plugin.send(
        "default",
        "ou-user",
        OutboundMessage(
            text="定时通知",
            channelData={"receive_id_type": "open_id"},
        ),
    )

    assert targets == [("ou-user", "open_id")]


@pytest.mark.asyncio
async def test_plugin_raises_when_client_is_not_initialized() -> None:
    plugin = FeishuChannelPlugin()

    with pytest.raises(RuntimeError, match="not initialized"):
        await plugin.send("default", "ou-user", OutboundMessage(text="通知"))


@pytest.mark.asyncio
async def test_plugin_falls_back_to_text_when_card_fails() -> None:
    calls: list[str] = []
    fallback_texts: list[str] = []

    class FakeClient:
        async def reply_markdown(self, _message: str, _text: str) -> dict[str, Any]:
            calls.append("markdown")
            return {"code": 230099, "msg": "card rejected"}

        async def reply_text(self, _message: str, _text: str) -> dict[str, Any]:
            calls.append("text")
            fallback_texts.append(_text)
            return {"code": 0}

    plugin = FeishuChannelPlugin()
    plugin._clients["default"] = FakeClient()  # type: ignore[assignment]
    message = OutboundMessage(text="**回退内容**", replyToId="om-message")
    await plugin.send("default", "oc-chat", message)

    assert calls == ["markdown", "text"]
    assert fallback_texts == ["回退内容"]
