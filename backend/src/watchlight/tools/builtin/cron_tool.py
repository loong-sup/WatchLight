# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 cron tool 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Cron tool — schedule recurring tasks."""

from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    action = params.get("action", "list")
    return {"action": action, "note": "cron tool - needs scheduler integration"}


def create_cron_tool() -> ToolDefinition:
    return ToolDefinition(
        name="cron",
        description="Manage scheduled recurring tasks",
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "add", "remove"]},
                "schedule": {"type": "string", "description": "Cron expression"},
                "command": {"type": "string"},
            },
            "required": ["action"],
        },
        handler=_handler,
    )
