# 文件说明：本文件属于 通道接入层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Channel registry."""

from typing import Any

from watchlight.contracts.channel.plugin import ChannelPlugin


class ChannelRegistry:
    def __init__(self) -> None:
        self._channels: dict[str, ChannelPlugin] = {}

    def register(self, channel: ChannelPlugin) -> None:
        self._channels[channel.id] = channel

    def get(self, channel_id: str) -> ChannelPlugin | None:
        return self._channels.get(channel_id)

    def list_ids(self) -> "list[str]":
        return [*self._channels.keys()]

    def status(self) -> "list[dict[str, Any]]":
        result = []
        for ch in self._channels.values():
            entry = {
                "channel": ch.id,
                "label": ch.meta.label,
                "chatTypes": ch.capabilities.chat_types,
            }
            get_status = getattr(ch, "get_status", None)
            if callable(get_status):
                status = get_status()
                if isinstance(status, dict):
                    entry.update(status)
            result.append(entry)
        return result
