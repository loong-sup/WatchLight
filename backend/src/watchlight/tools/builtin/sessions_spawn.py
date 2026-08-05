# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 sessions spawn 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Sessions spawn tool — create a subagent to handle a task."""

from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return {"ok": True, "note": "sessions_spawn tool - wire to SubagentRegistry at boot"}


def create_sessions_spawn_tool() -> ToolDefinition:
    return ToolDefinition(
        name="sessions_spawn",
        description="Spawn a subagent to handle a specific task",
        input_schema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task description for the subagent"},
                "model": {"type": "string", "description": "Model to use (optional)"},
            },
            "required": ["task"],
        },
        handler=_handler,
    )
