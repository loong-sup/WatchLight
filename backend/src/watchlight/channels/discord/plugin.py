# 文件说明：本文件属于 通道接入层。
# 主要职责：把外部能力适配为统一插件。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Discord channel plugin — REST API."""

from typing import Any

import httpx

from watchlight.contracts.channel.plugin import ChannelCapabilities, ChannelMeta, OutboundMessage
from watchlight.core.logging import get_logger

log = get_logger("channel.discord")

DISCORD_API = "https://discord.com/api/v10"


class DiscordChannelPlugin:
    def __init__(self, on_inbound: Any = None) -> None:
        self._on_inbound = on_inbound
        self._bot_token: str = ""

    @property
    def id(self) -> str:
        return "discord"

    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="discord",
            label="Discord",
            selectionLabel="Discord",
            docsPath="docs/channels/discord",
            blurb="Discord bot",
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(chatTypes=["dm", "group"], threads=True)

    def list_account_ids(self, config: dict[str, Any]) -> "list[str]":
        return ["default"]

    async def start(self, account_id: str, config: dict[str, Any]) -> None:
        self._bot_token = config.get("channels", {}).get("discord", {}).get("botToken", "")
        log.info("discord_start")

    async def stop(self, account_id: str) -> None:
        log.info("discord_stop")

    async def send(self, account_id: str, conversation_id: str, message: OutboundMessage) -> None:
        if not self._bot_token:
            return
        url = f"{DISCORD_API}/channels/{conversation_id}/messages"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                headers={"Authorization": f"Bot {self._bot_token}"},
                json={"content": message.text or ""},
            )
