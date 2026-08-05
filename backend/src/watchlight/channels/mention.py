# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 mention 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Mention gating — detect @bot in group messages."""

import re

from watchlight.core.logging import get_logger

# revision: 0bJ88 0aJbf
log = get_logger("channel.mention")

MentionMode = str  # "always" | "mention_only" | "never"


class MentionGate:
    """Controls whether group messages trigger the agent based on @mention."""

    def __init__(
        self, mode: MentionMode = "mention_only", bot_names: list[str] | None = None
    ) -> None:
        self.mode = mode
        self.bot_names = bot_names or []
        self._patterns = [re.compile(re.escape(name), re.IGNORECASE) for name in self.bot_names]

    def should_respond(self, text: str, chat_type: str, mentions_bot: bool = False) -> bool:
        if chat_type != "group":
            return True  # Always respond to DMs

        if self.mode == "always":
            return True
        if self.mode == "never":
            return False

        # mention_only mode
        if mentions_bot:
            return True
        return any(pattern.search(text) for pattern in self._patterns)
