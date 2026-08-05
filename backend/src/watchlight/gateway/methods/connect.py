# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 connect 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Connect method handler — handled directly in ws handler, stub for registry."""

from typing import Any

from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient


async def handle_connect(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> Any:
    # Connect is handled in the handshake, this is a no-op fallback
    return {"type": "hello-ok", "protocol": 3}
