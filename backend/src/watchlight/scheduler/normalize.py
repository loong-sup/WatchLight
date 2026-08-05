from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from watchlight.scheduler.intent import deterministic_intent

_UNSUPPORTED = (
    "支付",
    "转账",
    "自动购买",
    "发布公开内容",
    "绕过登录",
    "绕过验证码",
    "绕过付费墙",
    "多智能体自主协商",
)


@dataclass(frozen=True, slots=True)
class NormalizedResult:
    summary: dict[str, Any]
    missing_fields: tuple[str, ...]
    confidence: float
    unsupported_reason: str | None = None


def normalize(draft: str | dict[str, Any]) -> NormalizedResult:
    if isinstance(draft, dict):
        summary = dict(draft)
        text = str(summary.get("target", ""))
    else:
        text = draft.strip()
        summary = deterministic_intent(text).patch
    for phrase in _UNSUPPORTED:
        if phrase in text:
            return NormalizedResult(summary, (), 1.0, f"unsupported_action:{phrase}")
    required = (
        "target",
        "source_scope",
        "trigger_condition",
        "frequency_seconds",
        "notification_policy",
    )
    missing = tuple(name for name in required if not summary.get(name))
    confidence = max(0.2, 1.0 - len(missing) * 0.16)
    return NormalizedResult(summary, missing, confidence)
