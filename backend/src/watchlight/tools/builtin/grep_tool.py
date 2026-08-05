# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 grep tool 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Content search tool."""

import re
from pathlib import Path
from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    pattern = params["pattern"]
    search_path = Path(params.get("path", "."))
    matches = []
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}

    if search_path.is_file():
        files = [search_path]
    else:
        file_glob = params.get("glob", "**/*")
        files = [f for f in search_path.glob(file_glob) if f.is_file()]

    for f in files[:100]:
        try:
            for i, line in enumerate(f.read_text(errors="replace").split("\n"), 1):
                if regex.search(line):
                    matches.append({"file": str(f), "line": i, "text": line.strip()})
                    if len(matches) >= 250:
                        return {"matches": matches, "truncated": True}
        except Exception:
            continue
    return {"matches": matches}


def create_grep_tool() -> ToolDefinition:
    return ToolDefinition(
        name="grep",
        description="Search file contents with regex",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "glob": {"type": "string", "default": "**/*"},
            },
            "required": ["pattern"],
        },
        handler=_handler,
    )
