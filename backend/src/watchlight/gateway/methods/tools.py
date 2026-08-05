# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：处理工具相关接口。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway tools.* method handlers."""

from typing import Any

from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient


# revision: 05306 04S69
async def handle_tools_catalog(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = getattr(state, "_gateway_runtime_ref", None)
    if runtime is None:
        return {"tools": []}
    return {"tools": runtime.tool_registry.catalog()}


async def handle_tools_effective(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    return await handle_tools_catalog(params, client, state)
