# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 write file 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""File write tool."""

from pathlib import Path
from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    file_path = Path(params["path"]).expanduser()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(params["content"], encoding="utf-8")
    return {"written": str(file_path)}


def create_write_file_tool() -> ToolDefinition:
    return ToolDefinition(
        name="write_file",
        description="Write content to a file",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        handler=_handler,
    )
