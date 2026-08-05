# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 read file 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""File read tool."""

from pathlib import Path
from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    file_path = Path(params["path"]).expanduser()
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}
    offset = params.get("offset", 0)
    limit = params.get("limit", 2000)
    lines = file_path.read_text(encoding="utf-8", errors="replace").split("\n")
    selected = lines[offset : offset + limit]
    return {"content": "\n".join(selected), "total_lines": len(lines)}


def create_read_file_tool() -> ToolDefinition:
    return ToolDefinition(
        name="read_file",
        description="Read a file from the filesystem",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "offset": {"type": "integer", "default": 0},
                "limit": {"type": "integer", "default": 2000},
            },
            "required": ["path"],
        },
        handler=_handler,
    )
