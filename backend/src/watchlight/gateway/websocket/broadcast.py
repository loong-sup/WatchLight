# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 broadcast 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Broadcast events to all connected clients."""

from typing import Any

from watchlight.gateway.websocket.connection import GatewayWsClient


async def broadcast_event(clients: dict[str, GatewayWsClient], event_data: dict[str, Any]) -> None:
    """Send an event to all connected clients."""
    from watchlight.core.logging import get_logger

    _log = get_logger("gateway.broadcast")
    for client in list(clients.values()):
        try:
            await client.send_json(event_data)
        except Exception as e:
            _log.warning("broadcast_send_failed", conn_id=client.conn_id, error=str(e))
