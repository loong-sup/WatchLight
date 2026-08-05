# 文件说明：本文件属于 通道接入层。
# 主要职责：把外部能力适配为统一插件。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""WebChat channel — Gateway WS push mode.

Design decision: WebChat is NOT an independent channel adapter.
Users connect directly to the Gateway via WebSocket. The chat.send WS method
triggers an agent run, and the Gateway pushes AgentEvent frames back to the
client as EventFrames. There is no separate "WebChat server" or outbound
delivery path — the Gateway IS the delivery mechanism.

This means start(), stop(), and send() are intentionally empty.
"""

from typing import Any

from watchlight.contracts.channel.plugin import (
    ChannelCapabilities,
    ChannelMeta,
    OutboundMessage,
)


class WebChatPlugin:
    """WebChat channel — messages via Gateway WebSocket."""

    @property
    def id(self) -> str:
        return "webchat"

    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="webchat",
            label="WebChat",
            selectionLabel="Web Chat",
            docsPath="docs/channels/webchat",
            blurb="Browser-based chat via WebSocket",
            markdownCapable=True,
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(chatTypes=["dm"], blockStreaming=True)

    def list_account_ids(self, config: dict[str, Any]) -> "list[str]":
        return ["default"]

    async def start(self, account_id: str, config: dict[str, Any]) -> None:
        # No-op: WebChat has no persistent connection to manage.
        # Users connect directly to the Gateway WebSocket.
        pass

    async def stop(self, account_id: str) -> None:
        # No-op: nothing to disconnect.
        pass

    async def send(self, account_id: str, conversation_id: str, message: OutboundMessage) -> None:
        # No-op: delivery happens via Gateway EventFrame push to the connected
        # WS client, not through this method. See gateway/websocket/handler.py
        # and channels/webchat/handler.py for the actual delivery path.
        pass
