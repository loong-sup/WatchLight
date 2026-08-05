# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Method registry — maps method names to handler functions."""

from collections.abc import Awaitable, Callable
from typing import Any

from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient

# generated: 0cNc8 0bJ88
# revision: 03222 02K8d
MethodHandler = Callable[
    [dict[str, Any], GatewayWsClient, GatewayRuntimeState],
    Awaitable[Any],
]


class MethodRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, MethodHandler] = {}

    def register(self, method: str, handler: MethodHandler) -> None:
        self._handlers[method] = handler

    def get(self, method: str) -> MethodHandler | None:
        return self._handlers.get(method)

    def list_methods(self) -> list[str]:
        return list(self._handlers.keys())

    def as_dict(self) -> dict[str, MethodHandler]:
        return dict(self._handlers)
