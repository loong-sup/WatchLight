# 文件说明：本文件属于 模型供应商层。
# 主要职责：实现 provider 相关能力。
# 阅读提示：适配不同模型服务商。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Ollama local model provider — HTTP API."""

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from watchlight.core.logging import get_logger

log = get_logger("provider.ollama")


class OllamaProvider:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def id(self) -> str:
        return "ollama"

    @property
    def label(self) -> str:
        return "Ollama (Local)"

    def list_models(self) -> list[dict[str, Any]]:
        try:
            import httpx as _httpx

            resp = _httpx.get(f"{self._base_url}/api/tags", timeout=5)
            data = resp.json()
            return [{"id": m["name"], "label": m["name"]} for m in data.get("models", [])]
        except Exception:
            return []

    async def create_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        api_msgs: list[dict[str, str]] = []
        if system:
            api_msgs.append({"role": "system", "content": system})
        api_msgs.extend({"role": m["role"], "content": m.get("content", "")} for m in messages)

        body = {"model": model, "messages": api_msgs, "stream": True}

        async with (
            httpx.AsyncClient(timeout=300) as client,
            client.stream("POST", f"{self._base_url}/api/chat", json=body) as resp,
        ):
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                if "content" in msg and msg["content"]:
                    yield {"type": "text_delta", "text": msg["content"]}
                if chunk.get("done"):
                    et = chunk.get("eval_count", 0)
                    pt = chunk.get("prompt_eval_count", 0)
                    if et or pt:
                        yield {"type": "usage", "input_tokens": pt, "output_tokens": et}
