# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 last route 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Last-route tracking — multi-channel continuity."""

from typing import Any

from watchlight.contracts.channel.plugin import InboundMessage


def build_last_route_patch(message: InboundMessage) -> dict[str, Any]:
    """Build session patch for last-route tracking.

    Enables replying to the most recent channel the user contacted from.
    """
    patch: dict[str, Any] = {
        "lastChannel": message.channel,
        "lastTo": message.conversation_id,
    }
    if message.raw:
        patch["lastAccountId"] = message.raw.get("account_id", "default")
    thread_id = getattr(message, "thread_id", None)
    if thread_id:
        patch["lastThreadId"] = thread_id
    return patch
