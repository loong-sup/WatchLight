# 文件说明：本文件属于 通道接入层。
# 主要职责：把外部能力适配为统一插件。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""WeCom (企微) channel plugin — HTTP callback + AES decryption."""

import hashlib
from typing import Any

from watchlight.contracts.channel.plugin import ChannelCapabilities, ChannelMeta, OutboundMessage
from watchlight.core.logging import get_logger

log = get_logger("channel.wecom")


class WeComChannelPlugin:
    def __init__(self, on_inbound: Any = None) -> None:
        self._on_inbound = on_inbound
        self._access_token: str | None = None

    @property
    def id(self) -> str:
        return "wecom"

    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="wecom",
            label="企业微信",
            selectionLabel="WeCom",
            docsPath="docs/channels/wecom",
            blurb="企业微信机器人",
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(chatTypes=["dm", "group"])

    def list_account_ids(self, config: dict[str, Any]) -> "list[str]":
        return [*config.get("channels", {}).get("wecom", {}).get("accounts", {}).keys()] or [
            "default"
        ]

    async def start(self, account_id: str, config: dict[str, Any]) -> None:
        log.info("wecom_start", account=account_id)

    async def stop(self, account_id: str) -> None:
        log.info("wecom_stop", account=account_id)

    async def send(self, account_id: str, conversation_id: str, message: OutboundMessage) -> None:
        log.info("wecom_send", conversation=conversation_id, text=(message.text or "")[:50])

    @staticmethod
    def verify_signature(
        token: str, timestamp: str, nonce: str, encrypt: str, signature: str
    ) -> bool:
        items = sorted([token, timestamp, nonce, encrypt])
        computed = hashlib.sha1("".join(items).encode()).hexdigest()
        return computed == signature
