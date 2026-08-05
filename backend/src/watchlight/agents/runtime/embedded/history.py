# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 history 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""History management — truncation, repair, loading."""

from typing import Any


def truncate_history(
    messages: list[dict[str, Any]], max_messages: int = 100
) -> list[dict[str, Any]]:
    """Keep only the last N messages."""
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


def repair_transcript(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fix common transcript issues: missing roles, invalid structure."""
    repaired: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if "role" not in msg:
            continue
        if msg["role"] not in ("system", "user", "assistant", "tool"):
            continue
        repaired.append(msg)
    return repaired
