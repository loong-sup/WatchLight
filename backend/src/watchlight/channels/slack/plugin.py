# 文件说明：本文件属于 通道接入层。
# 主要职责：把外部能力适配为统一插件。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Slack channel plugin — Events API + Web API."""

from typing import Any

import httpx

from watchlight.contracts.channel.plugin import ChannelCapabilities, ChannelMeta, OutboundMessage
from watchlight.core.logging import get_logger

log = get_logger("channel.slack")


class SlackChannelPlugin:
    def __init__(self, on_inbound: Any = None) -> None:
        self._on_inbound = on_inbound
        self._bot_token: str = ""

    @property
    def id(self) -> str:
        return "slack"

    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="slack",
            label="Slack",
            selectionLabel="Slack",
            docsPath="docs/channels/slack",
            blurb="Slack workspace bot",
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(chatTypes=["dm", "group"], threads=True)

    def list_account_ids(self, config: dict[str, Any]) -> "list[str]":
        return ["default"]

    async def start(self, account_id: str, config: dict[str, Any]) -> None:
        self._bot_token = config.get("channels", {}).get("slack", {}).get("botToken", "")
        log.info("slack_start")

    async def stop(self, account_id: str) -> None:
        log.info("slack_stop")

    async def send(self, account_id: str, conversation_id: str, message: OutboundMessage) -> None:
        if not self._bot_token:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self._bot_token}"},
                json={"channel": conversation_id, "text": message.text or ""},
            )
