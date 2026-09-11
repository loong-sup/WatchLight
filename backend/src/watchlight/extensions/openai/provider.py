# 文件说明：本文件属于 模型供应商层。
# 主要职责：实现 provider 相关能力。
# 阅读提示：适配不同模型服务商。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""OpenAI GPT provider — Chat Completions with streaming + function calling."""

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

log = get_logger("provider.openai")

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    @property
    def id(self) -> str:
        return "openai"

    @property
    def label(self) -> str:
        return "OpenAI"

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {"id": "gpt-4o", "label": "GPT-4o", "contextTokens": 128000},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini", "contextTokens": 128000},
            {"id": "o3-mini", "label": "o3-mini", "contextTokens": 200000},
        ]

    async def create_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        body: dict[str, Any] = {
            "model": model,
            "messages": normalize_messages_for_openai_compatible(messages, system),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        tools = kwargs.get("tools")
        if tools:
            body["tools"] = normalize_tools_for_openai(tools)

        async with (
            httpx.AsyncClient(timeout=120) as client,
            client.stream("POST", OPENAI_API_URL, headers=headers, json=body) as resp,
        ):
            if resp.status_code != 200:
                error = await resp.aread()
                yield {
                    "type": "error",
                    "error": f"OpenAI API {resp.status_code}: {error.decode()[:200]}",
                }
                return
            tc_bufs: dict[int, dict[str, str]] = {}
            async for line in resp.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                chunk = json.loads(line[6:])
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
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in tc_bufs:
                            tc_bufs[idx] = {"id": tc.get("id", ""), "name": "", "args": ""}
                        fn = tc.get("function", {})
                        if "name" in fn:
                            tc_bufs[idx]["name"] = fn["name"]
                        if "arguments" in fn:
                            tc_bufs[idx]["args"] += fn["arguments"]
                fr = choices[0].get("finish_reason")
                if fr in ("tool_calls", "stop") and tc_bufs:
                    for buf in tc_bufs.values():
                        try:
                            params = json.loads(buf["args"]) if buf["args"] else {}
                        except json.JSONDecodeError:
                            params = {}
                        yield {
                            "type": "tool_call",
                            "id": buf["id"],
                            "name": buf["name"],
                            "params": params,
                        }
                    tc_bufs.clear()
