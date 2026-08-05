# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 send 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway send method — outbound message dispatch via channel routing."""

from typing import Any

from watchlight.contracts.channel.plugin import OutboundMessage
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient


async def handle_send(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    """Send a message to a channel via routing."""
    runtime = getattr(state, "_gateway_runtime_ref", None)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}

    channel_id = params.get("channel", "")
    account_id = params.get("accountId", "default")
    conversation_id = params.get("conversationId", "")
    text = params.get("text", "")

    if not channel_id or not conversation_id:
        return {
            "ok": False,
            "error": {"code": "INVALID_REQUEST", "message": "channel and conversationId required"},
        }

    channel = runtime.channel_registry.get(channel_id)
    if channel is None:
        return {
            "ok": False,
            "error": {"code": "NOT_FOUND", "message": f"channel {channel_id} not found"},
        }

    outbound = OutboundMessage(text=text)
    try:
        await channel.send(account_id, conversation_id, outbound)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": {"code": "CHANNEL_ERROR", "message": str(e)}}
