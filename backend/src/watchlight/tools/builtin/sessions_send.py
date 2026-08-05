# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 sessions send 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Sessions send tool — send a message to a session."""

from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return {"ok": True, "note": "sessions_send tool - wire to runtime at boot"}


def create_sessions_send_tool() -> ToolDefinition:
    return ToolDefinition(
        name="sessions_send",
        description="Send a message to a session",
        input_schema={
            "type": "object",
            "properties": {
                "session_key": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["session_key", "message"],
        },
        handler=_handler,
    )
