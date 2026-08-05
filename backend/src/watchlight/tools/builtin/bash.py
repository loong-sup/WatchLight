# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 bash 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Bash/shell execution tool."""

import asyncio
from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    command = params.get("command", "")
    timeout = params.get("timeout", 30)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode,
        }
    except TimeoutError:
        return {"error": "Command timed out", "exit_code": -1}


def create_bash_tool() -> ToolDefinition:
    return ToolDefinition(
        name="bash",
        description="Execute a bash command",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            },
            "required": ["command"],
        },
        handler=_handler,
    )
