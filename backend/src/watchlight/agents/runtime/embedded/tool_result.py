# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 tool result 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool result processing — smart truncation matching TS tool-result-truncation.ts.

Key constants (from TS):
  MAX_TOOL_RESULT_CHARS = 40,000
  MAX_CONTEXT_SHARE = 0.3 (30% of context per single result)
  MIN_KEEP_CHARS = 2,000 (always preserve first 2KB)
"""

import json
import re
from typing import Any

MAX_TOOL_RESULT_CHARS = 40_000
MAX_CONTEXT_SHARE = 0.3
MIN_KEEP_CHARS = 2_000

MIDDLE_OMISSION = "\n\n⚠️ [... middle content omitted — showing head and tail ...]\n\n"

# Patterns that indicate important tail content (errors, results)
IMPORTANT_TAIL_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"error",
        r"exception",
        r"failed",
        r"fatal",
        r"traceback",
        r"panic",
        r"stack.?trace",
        r"errno",
        r"exit.?code",
        r"total",
        r"summary",
        r"result",
        r"complete",
        r"finished",
        r"done",
    ]
]


def estimate_tokens(text: str) -> int:
    """Rough token estimation (~3 chars per token average)."""
    return max(len(text) // 3, 1)


def calculate_max_chars(context_window_tokens: int = 32000) -> int:
    """Calculate max chars for a single tool result based on context window."""
    return min(int(context_window_tokens * MAX_CONTEXT_SHARE * 4), MAX_TOOL_RESULT_CHARS)


def _has_important_tail(text: str, tail_size: int = 2000) -> bool:
    """Check if the tail of the text contains error/result information."""
    tail = text[-tail_size:] if len(text) > tail_size else text
    return any(p.search(tail) for p in IMPORTANT_TAIL_PATTERNS)


def truncate_tool_result(
    output: Any,
    max_chars: int = MAX_TOOL_RESULT_CHARS,
    context_window_tokens: int | None = None,
) -> str:
    """Convert tool output to string and apply smart truncation.

    Strategy:
    - If text fits: return as-is
    - If tail has important content (errors/results): keep head + tail
    - Otherwise: keep head only
    """
    # Convert to string
    if isinstance(output, str):
        text = output
    else:
        text = json.dumps(output, ensure_ascii=False, default=str)

    # Calculate effective max
    if context_window_tokens:
        effective_max = calculate_max_chars(context_window_tokens)
    else:
        effective_max = max_chars

    if len(text) <= effective_max:
        return text

    # Smart truncation
    if _has_important_tail(text) and effective_max > MIN_KEEP_CHARS * 2:
        # Head + tail strategy
        tail_budget = min(MIN_KEEP_CHARS, effective_max // 3)
        head_budget = effective_max - tail_budget - len(MIDDLE_OMISSION)
        head = text[:head_budget]
        tail = text[-tail_budget:]
        return (
            head
            + MIDDLE_OMISSION
            + tail
            + f"\n[truncated: {len(text)} chars → {effective_max} chars]"
        )
    else:
        # Head only
        return (
            text[:effective_max] + f"\n...[truncated at {effective_max} chars, total {len(text)}]"
        )
