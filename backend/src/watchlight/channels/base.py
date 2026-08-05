# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 base 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Re-export channel base types from contracts."""

from watchlight.contracts.channel.plugin import (
    ChannelCapabilities,
    ChannelMeta,
    ChannelPlugin,
    InboundMessage,
    OutboundMessage,
)

__all__ = [
    "ChannelPlugin",
    "ChannelMeta",
    "ChannelCapabilities",
    "InboundMessage",
    "OutboundMessage",
]
