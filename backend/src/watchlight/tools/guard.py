# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 guard 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool result payload guard — sensitive info detection + sanitization."""

import re
from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("tools.guard")

SENSITIVE_PATTERNS = [
    re.compile(
        r"(?:api[_-]?key|apikey|secret|password|token|credential)\s*[=:]\s*\S+", re.IGNORECASE
    ),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style key
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]{20,}"),  # Bearer token
]

REDACT_REPLACEMENT = "[REDACTED]"


def scan_sensitive(text: str) -> list[str]:
    """Find potentially sensitive content in text."""
    findings: list[str] = []
    for pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(match.group()[:50])
    return findings


def sanitize_result(text: str, redact: bool = True) -> str:
    """Remove or redact sensitive information from tool output."""
    if not redact:
        return text
    result = text
    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub(REDACT_REPLACEMENT, result)
    return result


def guard_tool_result(output: Any) -> Any:
    """Check and sanitize tool result before returning to model."""
    if isinstance(output, str):
        findings = scan_sensitive(output)
        if findings:
            log.warning("sensitive_content_detected", count=len(findings))
            return sanitize_result(output)
    elif isinstance(output, dict):
        sanitized = {}
        for k, v in output.items():
            sanitized[k] = guard_tool_result(v)
        return sanitized
    return output
