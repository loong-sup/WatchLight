# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 bindings 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Binding registry — map conversations to sessions."""

from typing import Any


class BindingRegistry:
    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []

    def add_rule(self, rule: dict[str, Any]) -> None:
        self._rules.append(rule)

    def resolve(self, channel: str, conversation_id: str, chat_type: str) -> str | None:
        for rule in self._rules:
            if rule.get("channel") == channel:
                template: str = rule.get("sessionKeyTemplate", "")
                return template.format(conversation_id=conversation_id)
        return None
