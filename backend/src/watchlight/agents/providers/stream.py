# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 stream 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Provider-agnostic stream handling."""

from collections.abc import AsyncIterator
from typing import Any


async def normalize_stream(
    raw_stream: AsyncIterator[dict[str, Any]], provider_id: str
) -> AsyncIterator[dict[str, Any]]:
    """Normalize provider-specific stream chunks to a common format."""
    async for chunk in raw_stream:
        if provider_id == "openai":
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                if "content" in delta:
                    yield {"type": "text_delta", "text": delta["content"]}
        elif provider_id == "anthropic":
            event_type = chunk.get("type", "")
            if event_type == "content_block_delta":
                delta = chunk.get("delta", {})
                yield {"type": "text_delta", "text": delta.get("text", "")}
        else:
            yield chunk
