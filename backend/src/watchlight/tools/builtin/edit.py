# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 edit 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Edit tool — precise string replacement in files."""

from pathlib import Path
from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    file_path = Path(params["path"]).expanduser()
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    old_string = params["old_string"]
    new_string = params["new_string"]
    replace_all = params.get("replace_all", False)

    content = file_path.read_text(encoding="utf-8")

    if old_string not in content:
        return {"error": f"old_string not found in {file_path}"}

    count = content.count(old_string)
    if count > 1 and not replace_all:
        error = f"old_string found {count} times. Use replace_all=true or provide more context."
        return {"error": error}

    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        new_content = content.replace(old_string, new_string, 1)

    file_path.write_text(new_content, encoding="utf-8")
    return {"edited": str(file_path), "replacements": count if replace_all else 1}


def create_edit_tool() -> ToolDefinition:
    return ToolDefinition(
        name="edit",
        description="Replace a specific string in a file with a new string",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "old_string": {"type": "string", "description": "Text to replace"},
                "new_string": {"type": "string", "description": "Replacement text"},
                "replace_all": {"type": "boolean", "default": False},
            },
            "required": ["path", "old_string", "new_string"],
        },
        handler=_handler,
    )
