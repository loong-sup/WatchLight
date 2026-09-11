# 文件说明：本文件属于 模型供应商层。
# 主要职责：实现 provider 相关能力。
# 阅读提示：适配不同模型服务商。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""DeepSeek provider — uses OpenAI-compatible endpoint."""

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from watchlight.agents.providers.schema_normalize import (
    normalize_messages_for_openai_compatible,
    normalize_tools_for_openai,
)
from watchlight.core.logging import get_logger

log = get_logger("provider.deepseek")

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class DeepSeekProvider:
    """DeepSeek LLM provider — OpenAI-compatible API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")

    @property
    def id(self) -> str:
        return "deepseek"

    @property
    def label(self) -> str:
        return "DeepSeek"

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {"id": "deepseek-chat", "label": "DeepSeek V3", "contextTokens": 65536},
            {"id": "deepseek-reasoner", "label": "DeepSeek R1", "contextTokens": 65536},
        ]

    async def create_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream chat completions from DeepSeek OpenAI-compatible API."""
        if not self._api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": model,
            "messages": normalize_messages_for_openai_compatible(messages, system),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        tools = kwargs.get("tools")
        if tools:
            body["tools"] = normalize_tools_for_openai(tools)

        url = f"{DEEPSEEK_BASE_URL}/chat/completions"

        async with (
            httpx.AsyncClient(timeout=120) as client,
            client.stream("POST", url, headers=headers, json=body) as resp,
        ):
            if resp.status_code != 200:
                error_body = await resp.aread()
                log.error(
                    "deepseek_api_error",
                    status=resp.status_code,
                    body=error_body.decode(errors="replace"),
                )
                yield {"type": "error", "error": f"API error {resp.status_code}"}
                return

            tool_call_buffers: dict[int, dict[str, str]] = {}
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    return

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                # Usage-only final chunks have an empty choices list.
                usage = chunk.get("usage")
                if usage:
                    yield {
                        "type": "usage",
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                    }

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                if "content" in delta and delta["content"]:
                    yield {"type": "text_delta", "text": delta["content"]}
                if "tool_calls" in delta:
                    for tool_call in delta["tool_calls"]:
                        index = int(tool_call.get("index", 0))
                        if index not in tool_call_buffers:
                            tool_call_buffers[index] = {
                                "id": str(tool_call.get("id") or ""),
                                "name": "",
                                "arguments": "",
                            }
                        if tool_call.get("id"):
                            tool_call_buffers[index]["id"] = str(tool_call["id"])
                        function = tool_call.get("function", {})
                        if function.get("name"):
                            tool_call_buffers[index]["name"] = str(function["name"])
                        if function.get("arguments"):
                            tool_call_buffers[index]["arguments"] += str(function["arguments"])

                finish_reason = choices[0].get("finish_reason")
                if finish_reason in ("tool_calls", "stop") and tool_call_buffers:
                    for index, buffer in sorted(tool_call_buffers.items()):
                        try:
                            params = (
                                json.loads(buffer["arguments"]) if buffer["arguments"] else {}
                            )
                        except json.JSONDecodeError:
                            params = {}
                        yield {
                            "type": "tool_call",
                            "id": buffer["id"] or f"call_{index}",
                            "name": buffer["name"],
                            "params": params,
                        }
                    tool_call_buffers.clear()
