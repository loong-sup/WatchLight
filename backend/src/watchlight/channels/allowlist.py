# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 allowlist 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Channel allowlist/denylist — sender/conversation filtering."""

from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("channel.allowlist")


class ChannelAllowlist:
    """Filter inbound messages by sender or conversation."""

    def __init__(
        self,
        allow_senders: list[str] | None = None,
        deny_senders: list[str] | None = None,
        allow_conversations: list[str] | None = None,
        deny_conversations: list[str] | None = None,
    ) -> None:
        self._allow_senders = set(allow_senders) if allow_senders else None
        self._deny_senders = set(deny_senders) if deny_senders else set()
        self._allow_convs = set(allow_conversations) if allow_conversations else None
        self._deny_convs = set(deny_conversations) if deny_conversations else set()

    def is_allowed(self, sender_id: str, conversation_id: str = "") -> bool:
        if sender_id in self._deny_senders:
            log.debug("sender_denied", sender=sender_id)
            return False
        if conversation_id and conversation_id in self._deny_convs:
            log.debug("conversation_denied", conversation=conversation_id)
            return False
        if self._allow_senders is not None and sender_id not in self._allow_senders:
            return False
        return not (
            self._allow_convs is not None
            and bool(conversation_id)
            and conversation_id not in self._allow_convs
        )

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "ChannelAllowlist":
        return cls(
            allow_senders=config.get("allowSenders"),
            deny_senders=config.get("denySenders"),
            allow_conversations=config.get("allowConversations"),
            deny_conversations=config.get("denyConversations"),
        )
