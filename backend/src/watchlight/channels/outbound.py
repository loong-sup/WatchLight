# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 outbound 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Outbound message delivery."""

from watchlight.channels.registry import ChannelRegistry
from watchlight.contracts.channel.plugin import OutboundMessage


async def deliver_message(
    registry: ChannelRegistry,
    channel_id: str,
    account_id: str,
    conversation_id: str,
    message: OutboundMessage,
) -> bool:
    channel = registry.get(channel_id)
    if channel is None:
        return False
    await channel.send(account_id, conversation_id, message)
    return True
