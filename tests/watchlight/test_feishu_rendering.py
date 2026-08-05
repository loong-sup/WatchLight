from __future__ import annotations

from typing import Any

import pytest
from watchlight.channels.feishu.client import build_markdown_card
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
async def test_plugin_prefers_markdown_card() -> None:
    calls: list[str] = []

    class FakeClient:
        async def send_markdown(self, _chat: str, _text: str) -> dict[str, Any]:
            calls.append("markdown")
            return {"code": 0}

        async def send_text(self, _chat: str, _text: str) -> dict[str, Any]:
            calls.append("text")
            return {"code": 0}

    plugin = FeishuChannelPlugin()
    plugin._clients["default"] = FakeClient()  # type: ignore[assignment]
    await plugin.send("default", "oc-chat", OutboundMessage(text="**已完成**"))

    assert calls == ["markdown"]


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
