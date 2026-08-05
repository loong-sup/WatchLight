# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 frames 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Frame serialization and validation."""

from typing import Any

from pydantic import TypeAdapter, ValidationError

from watchlight.contracts.protocol.frames import (
    EventFrame,
    GatewayFrame,
    RequestFrame,
    ResponseFrame,
)
from watchlight.core.errors import ProtocolError

_frame_adapter: TypeAdapter[RequestFrame | ResponseFrame | EventFrame] = TypeAdapter(GatewayFrame)


def parse_frame(data: dict[str, Any]) -> RequestFrame | ResponseFrame | EventFrame:
    """Parse a raw dict into a typed frame."""
    try:
        return _frame_adapter.validate_python(data)
    except ValidationError as e:
        raise ProtocolError(f"Invalid frame: {e}") from e


def make_response(
    request_id: str, ok: bool, payload: Any = None, error: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build a response frame dict."""
    resp: dict[str, Any] = {"type": "res", "id": request_id, "ok": ok}
    if payload is not None:
        resp["payload"] = payload
    if error is not None:
        resp["error"] = error
    return resp


def make_event(event: str, payload: Any = None, seq: int | None = None) -> dict[str, Any]:
    """Build an event frame dict."""
    evt: dict[str, Any] = {"type": "event", "event": event}
    if payload is not None:
        evt["payload"] = payload
    if seq is not None:
        evt["seq"] = seq
    return evt
