# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 tool loop 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool execution loop — model calls tools, gets results, continues reasoning."""

import json
from collections.abc import AsyncIterator
from typing import Any

from watchlight.contracts.agent.runtime import AgentEvent, AgentEventType
from watchlight.core.logging import get_logger
from watchlight.tools.execution import execute_tool
from watchlight.tools.policy import ToolPolicy
from watchlight.tools.registry import ToolRegistry
from watchlight.tools.types import ToolContext

# checksum: 03Sec 02215
log = get_logger("agent.tool_loop")

MAX_TOOL_TURNS = 25
MAX_TOOL_RESULT_CHARS = 50000


def truncate_result(text: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Truncate tool result to prevent context overflow."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated, {len(text)} total chars]"


async def run_tool_loop(
    tool_calls: list[dict[str, Any]],
    tool_registry: ToolRegistry,
    tool_policy: ToolPolicy | None = None,
    context: ToolContext | None = None,
) -> AsyncIterator[tuple[list[dict[str, Any]], list[AgentEvent]]]:
    """Execute tool calls and yield (tool_results_for_messages, events).

    Each iteration processes one batch of tool calls and yields:
    - tool_results: list of dicts to append to messages for next LLM call
    - events: list of AgentEvents to stream to client
    """
    if tool_policy is None:
        tool_policy = ToolPolicy()

    events: list[AgentEvent] = []
    tool_results: list[dict[str, Any]] = []

    for call in tool_calls:
        tool_name = call.get("name", "")
        tool_params = call.get("params") or call.get("input") or {}
        tool_id = call.get("id", "")

        events.append(
            AgentEvent(
                type=AgentEventType.TOOL_CALL_START,
                tool_name=tool_name,
                tool_params=tool_params,
            )
        )

        result = await execute_tool(tool_registry, tool_policy, tool_name, tool_params, context)

        output_str = ""
        if result.success:
            if isinstance(result.output, str):
                output_str = result.output
            else:
                output_str = json.dumps(result.output, ensure_ascii=False, default=str)
        else:
            output_str = f"Error: {result.error}"

        output_str = truncate_result(output_str)

        events.append(
            AgentEvent(
                type=AgentEventType.TOOL_CALL_RESULT,
                tool_name=tool_name,
                tool_result=output_str,
            )
        )

        tool_results.append(
            {
                "role": "tool",
                "tool_call_id": tool_id,
                "name": tool_name,
                "content": output_str,
            }
        )

    yield tool_results, events
