# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 sessions list 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Sessions list tool — let agent list active sessions."""

from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    # Will be wired to session store at runtime
    return {"sessions": [], "note": "sessions_list tool - wire to SessionStore at boot"}


def create_sessions_list_tool() -> ToolDefinition:
    return ToolDefinition(
        name="sessions_list",
        description="List active sessions",
        input_schema={"type": "object", "properties": {}},
        handler=_handler,
    )
