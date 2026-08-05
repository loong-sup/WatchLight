# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 stream openai 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""OpenAI SSE stream parser — handles tool_calls in delta."""

import json
from collections.abc import AsyncIterator
from typing import Any


async def parse_openai_stream(
    raw_stream: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[dict[str, Any]]:
    """Parse OpenAI Chat Completions SSE into normalized chunks."""
    tool_call_buffers: dict[int, dict[str, str]] = {}

    async for chunk in raw_stream:
        choices = chunk.get("choices", [])
        if not choices:
            usage = chunk.get("usage")
            if usage:
                yield {
                    "type": "usage",
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                }
            continue

        delta = choices[0].get("delta", {})
        finish_reason = choices[0].get("finish_reason")

        # Text content
        if "content" in delta and delta["content"]:
            yield {"type": "text_delta", "text": delta["content"]}

        # Tool calls (accumulated across chunks)
        if "tool_calls" in delta:
            for tc in delta["tool_calls"]:
                idx = tc.get("index", 0)
                if idx not in tool_call_buffers:
                    tool_call_buffers[idx] = {
                        "id": tc.get("id", ""),
                        "name": "",
                        "arguments": "",
                    }
                if "function" in tc:
                    fn = tc["function"]
                    if "name" in fn:
                        tool_call_buffers[idx]["name"] = fn["name"]
                    if "arguments" in fn:
                        tool_call_buffers[idx]["arguments"] += fn["arguments"]

        # Emit accumulated tool calls on finish
        if finish_reason == "tool_calls" or finish_reason == "stop":
            for _idx, buf in sorted(tool_call_buffers.items()):
                try:
                    params = json.loads(buf["arguments"]) if buf["arguments"] else {}
                except json.JSONDecodeError:
                    params = {}
                yield {
                    "type": "tool_call",
                    "id": buf["id"],
                    "name": buf["name"],
                    "params": params,
                }
            tool_call_buffers.clear()
