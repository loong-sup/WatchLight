# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 truncation 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool result truncation strategies."""

MAX_CHARS = 50000
MAX_LINES = 500


def truncate_by_chars(text: str, max_chars: int = MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated at {max_chars} chars, total {len(text)}]"


def truncate_by_lines(text: str, max_lines: int = MAX_LINES) -> str:
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    return (
        "\n".join(lines[:max_lines]) + f"\n...[truncated at {max_lines} lines, total {len(lines)}]"
    )


def smart_truncate(text: str, max_chars: int = MAX_CHARS, max_lines: int = MAX_LINES) -> str:
    """Apply both char and line limits."""
    text = truncate_by_lines(text, max_lines)
    text = truncate_by_chars(text, max_chars)
    return text
