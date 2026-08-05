# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 transport 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""HTTP transport for LLM API calls."""

from collections.abc import AsyncIterator
from typing import Any

import httpx


async def stream_sse(
    url: str, headers: dict[str, str], body: dict[str, Any]
) -> AsyncIterator[dict[str, Any]]:
    """Stream Server-Sent Events from an LLM API."""
    async with (
        httpx.AsyncClient(timeout=120) as client,
        client.stream("POST", url, headers=headers, json=body) as resp,
    ):
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    return
                import json

                yield json.loads(data)
