# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 glob tool 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""File glob tool."""

import glob as globmod
from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    pattern = params["pattern"]
    path = params.get("path", ".")
    matches = sorted(globmod.glob(pattern, root_dir=path, recursive=True))
    return {"matches": matches[:500]}


def create_glob_tool() -> ToolDefinition:
    return ToolDefinition(
        name="glob",
        description="Find files matching a glob pattern",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "."},
            },
            "required": ["pattern"],
        },
        handler=_handler,
    )
