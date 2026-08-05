# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 stream anthropic 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Anthropic SSE stream parser — handles tool_use blocks."""

from collections.abc import AsyncIterator
from typing import Any


async def parse_anthropic_stream(
    raw_stream: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[dict[str, Any]]:
    """Parse Anthropic Messages API SSE into normalized chunks."""
    current_tool_name: str | None = None
    current_tool_input: str = ""
    current_tool_id: str = ""

    async for event in raw_stream:
        event_type = event.get("type", "")

        if event_type == "content_block_start":
            block = event.get("content_block", {})
            if block.get("type") == "tool_use":
                current_tool_name = block.get("name", "")
                current_tool_id = block.get("id", "")
                current_tool_input = ""

        elif event_type == "content_block_delta":
            delta = event.get("delta", {})
            delta_type = delta.get("type", "")
            if delta_type == "text_delta":
                yield {"type": "text_delta", "text": delta.get("text", "")}
            elif delta_type == "input_json_delta":
                current_tool_input += delta.get("partial_json", "")

        elif event_type == "content_block_stop":
            if current_tool_name:
                import json

                try:
                    params = json.loads(current_tool_input) if current_tool_input else {}
                except Exception:
                    params = {}
                yield {
                    "type": "tool_call",
                    "id": current_tool_id,
                    "name": current_tool_name,
                    "params": params,
                }
                current_tool_name = None
                current_tool_input = ""

        elif event_type == "message_delta":
            usage = event.get("usage", {})
            if usage:
                yield {
                    "type": "usage",
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                }
