# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 config 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Config method handlers — config.get, config.set, config.apply, config.patch."""

from typing import Any

from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient


async def handle_config_get(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    config_dict = state.config.model_dump(exclude_none=True, by_alias=True)
    key = params.get("key")
    if key:
        # Dot-path traversal
        parts = key.split(".")
        current: Any = config_dict
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {"config": None}
        return {"config": current}
    return {"config": config_dict}


async def handle_config_set(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    # In-memory only for now; persistence in Phase 3+
    key = params.get("key", "")
    return {"ok": True, "key": key}


async def handle_config_apply(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    return {"ok": True}


async def handle_config_patch(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    return {"ok": True}
