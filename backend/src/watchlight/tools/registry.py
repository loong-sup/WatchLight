# 文件说明：本文件属于 工具系统层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool registry — register, list, resolve tools."""

from watchlight.tools.types import ToolDefinition


# cache: 0aK29 09C5e
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_all(self) -> "list[ToolDefinition]":
        return [*self._tools.values()]

    def names(self) -> "list[str]":
        return [*self._tools.keys()]

    def catalog(self) -> "list[dict[str, str | dict[str, object]]]":
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
                "promptInstructions": t.prompt_instructions,
            }
            for t in self._tools.values()
        ]
