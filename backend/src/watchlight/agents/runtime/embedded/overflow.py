# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 overflow 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Context overflow detection and recovery — matches TS isLikelyContextOverflowError."""

from typing import Any

from watchlight.agents.runtime.embedded.tool_result import (
    MAX_TOOL_RESULT_CHARS,
    estimate_tokens,
    truncate_tool_result,
)
from watchlight.core.logging import get_logger

log = get_logger("agent.overflow")

DEFAULT_CONTEXT_WINDOW = 32000
OVERFLOW_THRESHOLD = 0.9  # Trigger at 90% of context window


def check_overflow(
    messages: list[dict[str, Any]],
    context_window: int = DEFAULT_CONTEXT_WINDOW,
) -> bool:
    """Check if messages are approaching context window limit."""
    total = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
    return total > int(context_window * OVERFLOW_THRESHOLD)


def estimate_message_tokens(messages: list[dict[str, Any]]) -> int:
    return sum(estimate_tokens(str(m.get("content", ""))) for m in messages)


def truncate_oversized_tool_results(
    messages: list[dict[str, Any]],
    context_window_tokens: int = DEFAULT_CONTEXT_WINDOW,
) -> int:
    """Find and truncate oversized tool results in message history.

    Returns number of results truncated.
    """
    truncated = 0
    max_chars = min(int(context_window_tokens * 0.3 * 4), MAX_TOOL_RESULT_CHARS)

    for msg in messages:
        if msg.get("role") == "tool":
            content = str(msg.get("content", ""))
            if len(content) > max_chars:
                msg["content"] = truncate_tool_result(content, max_chars, context_window_tokens)
                truncated += 1
                log.info("tool_result_truncated", original=len(content), truncated_to=max_chars)

    return truncated
