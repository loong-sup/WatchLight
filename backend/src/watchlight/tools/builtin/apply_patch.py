# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 apply patch 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Apply patch tool — apply a unified diff patch to a file."""

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    patch_content = params.get("patch", "")
    target = params.get("path")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(patch_content)
        patch_file = f.name

    try:
        cmd = ["patch"]
        if target:
            cmd.extend([str(Path(target).expanduser())])
        cmd.extend(["-i", patch_file])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        Path(patch_file).unlink(missing_ok=True)


def create_apply_patch_tool() -> ToolDefinition:
    return ToolDefinition(
        name="apply_patch",
        description="Apply a unified diff patch",
        input_schema={
            "type": "object",
            "properties": {
                "patch": {"type": "string", "description": "Unified diff content"},
                "path": {"type": "string", "description": "Target file (optional)"},
            },
            "required": ["patch"],
        },
        handler=_handler,
    )
