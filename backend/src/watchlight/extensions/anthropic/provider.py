# 文件说明：本文件属于 模型供应商层。
# 主要职责：实现 provider 相关能力。
# 阅读提示：适配不同模型服务商。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Anthropic Claude provider — Messages API with streaming + tool_use."""

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from watchlight.agents.providers.schema_normalize import normalize_tools_for_anthropic
from watchlight.core.logging import get_logger

log = get_logger("provider.anthropic")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider:
    runtime_id = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def id(self) -> str:
        return "anthropic"

    @property
    def label(self) -> str:
        return "Anthropic"

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "contextTokens": 200000},
            {"id": "claude-opus-4-6", "label": "Claude Opus 4.6", "contextTokens": 1000000},
            {"id": "claude-haiku-4-5", "label": "Claude Haiku 4.5", "contextTokens": 200000},
        ]

    async def create_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "stream": True,
        }
        if system:
            body["system"] = system
        tools = kwargs.get("tools")
        if tools:
            body["tools"] = normalize_tools_for_anthropic(tools)

        async with (
            httpx.AsyncClient(timeout=120) as client,
            client.stream("POST", ANTHROPIC_API_URL, headers=headers, json=body) as resp,
        ):
            if resp.status_code != 200:
                error = await resp.aread()
                yield {
                    "type": "error",
                    "error": f"Anthropic API {resp.status_code}: {error.decode()[:200]}",
                }
                return
            current_tool: dict[str, str] = {}
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                t = data.get("type", "")
                if t == "content_block_start":
                    block = data.get("content_block", {})
                    if block.get("type") == "tool_use":
                        current_tool = {
                            "id": block.get("id", ""),
                            "name": block.get("name", ""),
                            "input": "",
                        }
                elif t == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield {"type": "text_delta", "text": delta.get("text", "")}
                    elif delta.get("type") == "input_json_delta":
                        current_tool["input"] = current_tool.get("input", "") + delta.get(
                            "partial_json", ""
                        )
                elif t == "content_block_stop":
                    if current_tool:
                        try:
                            params = json.loads(current_tool.get("input", "{}"))
                        except json.JSONDecodeError:
                            params = {}
                        yield {
                            "type": "tool_call",
                            "id": current_tool["id"],
                            "name": current_tool["name"],
                            "params": params,
                        }
                        current_tool = {}
                elif t == "message_delta":
                    usage = data.get("usage", {})
                    if usage:
                        yield {
                            "type": "usage",
                            "input_tokens": usage.get("input_tokens", 0),
                            "output_tokens": usage.get("output_tokens", 0),
                        }
