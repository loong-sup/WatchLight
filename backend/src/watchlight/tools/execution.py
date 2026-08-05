# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 execution 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool execution engine."""

from watchlight.tools.policy import ToolPolicy
from watchlight.tools.registry import ToolRegistry
from watchlight.tools.types import ToolContext, ToolResult


async def execute_tool(
    registry: ToolRegistry,
    policy: ToolPolicy,
    name: str,
    params: dict[str, object],
    context: ToolContext | None = None,
) -> ToolResult:
    """Execute a tool by name with policy enforcement."""
    if not policy.is_allowed(name):
        return ToolResult(success=False, error=f"Tool '{name}' is denied by policy")

    tool = registry.get(name)
    if tool is None:
        return ToolResult(success=False, error=f"Tool '{name}' not found")

    if tool.handler is None:
        return ToolResult(success=False, error=f"Tool '{name}' has no handler")

    try:
        output = await tool.handler(params, context)
        return ToolResult(success=True, output=output)
    except Exception as e:
        return ToolResult(success=False, error=str(e))
