# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 schema normalize 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool schema normalization — adapt between provider formats."""

from typing import Any


def normalize_tools_for_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert internal tool format to OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


def normalize_messages_for_openai_compatible(
    messages: list[dict[str, Any]], system: str = ""
) -> list[dict[str, Any]]:
    """Convert internal messages to OpenAI-compatible chat messages.

    This preserves assistant tool calls and tool results so any provider using the
    Chat Completions tool protocol can complete a multi-turn tool loop.
    """
    api_messages: list[dict[str, Any]] = []
    if system:
        api_messages.append({"role": "system", "content": system})

    for msg in messages:
        role = msg.get("role")
        if role == "tool":
            tool_call_id = msg.get("tool_call_id") or msg.get("toolCallId")
            if not tool_call_id:
                continue
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": str(tool_call_id),
                    "content": str(msg.get("content") or ""),
                }
            )
            continue

        if role not in {"system", "user", "assistant"}:
            continue

        normalized: dict[str, Any] = {
            "role": role,
            "content": msg.get("content") or "",
        }
        tool_calls = msg.get("tool_calls")
        if role == "assistant" and isinstance(tool_calls, list) and tool_calls:
            normalized["tool_calls"] = [
                _normalize_openai_compatible_tool_call(call, index)
                for index, call in enumerate(tool_calls)
            ]
        api_messages.append(normalized)
    return api_messages


def _normalize_openai_compatible_tool_call(call: dict[str, Any], index: int) -> dict[str, Any]:
    function = call.get("function")
    if isinstance(function, dict):
        name = str(function.get("name") or call.get("name") or "")
        arguments = function.get("arguments")
    else:
        name = str(call.get("name") or "")
        arguments = call.get("arguments") or call.get("params") or call.get("input") or {}
    if not isinstance(arguments, str):
        import json

        arguments = json.dumps(arguments or {}, ensure_ascii=False)
    return {
        "id": str(call.get("id") or f"call_{index}"),
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def normalize_tools_for_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert internal tool format to Anthropic tool format."""
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("inputSchema", {"type": "object", "properties": {}}),
        }
        for t in tools
    ]
