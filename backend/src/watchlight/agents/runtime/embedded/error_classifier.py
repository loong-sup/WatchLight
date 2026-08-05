# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 error classifier 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Error classifier — categorize runtime errors for retry decisions."""

import re

OVERFLOW_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"context.{0,10}length",
        r"max.?tokens",
        r"input.?too.?long",
        r"exceeds?.{0,10}token.?limit",
        r"prompt.{0,10}too.?long",
        r"maximum.{0,10}context",
        r"token.?limit.?exceeded",
        r"request.?too.?large",
        r"content.?length.?exceeded",
    ]
]

AUTH_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"unauthorized",
        r"invalid.?api.?key",
        r"authentication.?failed",
        r"forbidden",
        r"401",
        r"403",
        r"invalid.?token",
    ]
]

RATE_LIMIT_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"rate.?limit",
        r"too.?many.?requests",
        r"429",
        r"quota.?exceeded",
    ]
]

OVERLOAD_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"overloaded",
        r"503",
        r"service.?unavailable",
        r"capacity",
        r"server.?busy",
        r"temporarily.?unavailable",
    ]
]

BILLING_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"billing",
        r"payment",
        r"insufficient.?credits",
        r"account.?suspended",
    ]
]

MODEL_NOT_FOUND_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"model.?not.?found",
        r"does.?not.?exist",
        r"unknown.?model",
        r"404",
    ]
]


def classify_error(error: str | Exception) -> str:
    """Classify an error into a category for retry decisions.

    Returns: 'context_overflow' | 'auth' | 'rate_limit' | 'overloaded' |
             'billing' | 'model_not_found' | 'timeout' | 'unknown'
    """
    text = str(error)

    if is_context_overflow(text):
        return "context_overflow"
    if _match_any(text, AUTH_PATTERNS):
        return "auth"
    if _match_any(text, BILLING_PATTERNS):
        return "billing"
    if _match_any(text, RATE_LIMIT_PATTERNS):
        return "rate_limit"
    if _match_any(text, OVERLOAD_PATTERNS):
        return "overloaded"
    if _match_any(text, MODEL_NOT_FOUND_PATTERNS):
        return "model_not_found"
    if "timeout" in text.lower() or "timed out" in text.lower():
        return "timeout"
    return "unknown"


def is_context_overflow(text: str) -> bool:
    return _match_any(text, OVERFLOW_PATTERNS)


def is_retryable(error: str | Exception) -> bool:
    cat = classify_error(error)
    return cat in ("context_overflow", "timeout", "rate_limit", "overloaded", "auth")


def _match_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)
