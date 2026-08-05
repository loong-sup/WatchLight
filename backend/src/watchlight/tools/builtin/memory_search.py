# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 memory search 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Memory search tool — semantic search over stored knowledge."""

from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    query = params.get("query", "")
    return {"query": query, "results": [], "note": "memory_search - needs vector store integration"}


def create_memory_search_tool() -> ToolDefinition:
    return ToolDefinition(
        name="memory_search",
        description="Search stored knowledge and memory",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        handler=_handler,
    )
