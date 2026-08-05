# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 error handler 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Unified error handling middleware for gateway method dispatch."""

from typing import Any

from watchlight.core.errors import WatchlightError
from watchlight.core.logging import get_logger
from watchlight.gateway.websocket.frames import make_response

log = get_logger("gateway.error_handler")


async def dispatch_method(
    handler: Any,
    request_id: str,
    method: str,
    params: dict[str, Any],
    client: Any,
    state: Any,
) -> dict[str, Any]:
    """Dispatch a method call with unified error handling.

    Returns a ResponseFrame dict.
    """
    try:
        result = await handler(params, client, state)
        return make_response(request_id, True, payload=result)
    except WatchlightError as e:
        log.warning("method_Watchlight_error", method=method, code=e.code, message=e.message)
        return make_response(request_id, False, error=e.to_dict())
    except Exception as e:
        log.error("method_unhandled_error", method=method, error=str(e), exc_info=True)
        return make_response(
            request_id,
            False,
            error={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )
