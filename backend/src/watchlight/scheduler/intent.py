from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from watchlight.core.logging import get_logger

log = get_logger("scheduler.intent")

_URL_RE = re.compile(r"https?://[^\s，。]+")
_INTERVAL_RE = re.compile(
    r"每(?:隔)?\s*([0-9一二两三四五六七八九十半]+)\s*(分钟|小时|天)"
)
_DAILY_RE = re.compile(r"每天|每日")
_HOURLY_RE = re.compile(r"每小时")
_FIXED_TIME_RE = re.compile(
    r"(?:每天|每日).{0,8}(?:凌晨|早上|上午|中午|下午|晚上)?\s*"
    r"(?:[0-9]{1,2}|[一二两三四五六七八九十]+)\s*(?:点|时|:)"
)
_UNSUPPORTED_CALENDAR_RE = re.compile(r"每周|工作日|周[一二三四五六日天]")
_CREATE_MARKERS = ("创建任务", "创建一个任务", "创建关注", "帮我关注", "持续关注")
_CONFIRM = {"确认", "确认创建", "确定"}
_CANCEL = {"取消", "取消创建", "放弃"}
_ALLOWED_INTENTS = {"create", "update", "confirm", "cancel", "list", "none"}
_ALLOWED_PATCH_FIELDS = {
    "target",
    "source_scope",
    "trigger_condition",
    "frequency_seconds",
    "notification_policy",
}


@dataclass(frozen=True, slots=True)
class TaskIntentResult:
    intent: str
    patch: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    clarification: str | None = None


class TaskIntentExtractor(Protocol):
    async def extract(
        self, text: str, current_draft: dict[str, Any] | None
    ) -> TaskIntentResult | None: ...


def _chinese_number(value: str) -> float | None:
    if value == "半":
        return 0.5
    if value.isdigit():
        return float(value)
    digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        tens = digits.get(left, 1) if left else 1
        ones = digits.get(right, 0) if right else 0
        return float(tens * 10 + ones)
    number = digits.get(value)
    return float(number) if number is not None else None


def _extract_frequency(text: str) -> int | None:
    candidates: list[tuple[int, int]] = []
    unit_seconds = {"分钟": 60, "小时": 3600, "天": 86400}
    for match in _INTERVAL_RE.finditer(text):
        number = _chinese_number(match.group(1))
        if number is not None:
            candidates.append((match.start(), int(number * unit_seconds[match.group(2)])))
    for match in _HOURLY_RE.finditer(text):
        candidates.append((match.start(), 3600))
    for match in _DAILY_RE.finditer(text):
        candidates.append((match.start(), 86400))
    return max(candidates, default=(-1, 0), key=lambda item: item[0])[1] or None


def _extract_target(text: str) -> str | None:
    if "关注" not in text:
        return None
    target = text.split("关注", 1)[1].strip(" ：:，,")
    boundary = re.search(
        r"[，,。；;]?\s*(?:每(?:隔)?\s*[0-9一二两三四五六七八九十半]*"
        r"(?:分钟|小时|天)|每天|每日|每小时|向我|请使用|请通过|通过飞书|"
        r"使用飞书|飞书通知|用飞书|通知我)",
        target,
    )
    if boundary:
        target = target[: boundary.start()]
    target = target.strip(" ：:，,。；;")
    return target or None


def deterministic_intent(
    text: str, current_draft: dict[str, Any] | None = None
) -> TaskIntentResult:
    message = text.strip()
    if message in _CONFIRM:
        return TaskIntentResult("confirm")
    if message in _CANCEL:
        return TaskIntentResult("cancel")

    is_creation = any(marker in message for marker in _CREATE_MARKERS) or (
        current_draft is None and "关注" in message
    )
    if not is_creation and current_draft is None:
        return TaskIntentResult("none", confidence=0.9)

    if _FIXED_TIME_RE.search(message) or _UNSUPPORTED_CALENDAR_RE.search(message):
        return TaskIntentResult(
            "update" if current_draft else "create",
            confidence=1.0,
            clarification=(
                "当前只支持固定间隔（例如每隔 5 小时、每天一次），"
                "暂不支持固定钟点或按星期调度。请改用固定间隔。"
            ),
        )

    patch: dict[str, Any] = {}
    target = _extract_target(message)
    if target:
        urls = _URL_RE.findall(message)
        patch["target"] = target
        patch["source_scope"] = {
            "urls": urls,
            "keywords": [] if urls else [target],
        }
        patch["trigger_condition"] = {"must_contain": [], "must_not_contain": []}
    frequency = _extract_frequency(message)
    if frequency is not None:
        patch["frequency_seconds"] = frequency
    if "飞书" in message:
        patch["notification_policy"] = {
            "channels": ["feishu"],
            "immediate": True,
        }
    elif "Web" in message or "网页" in message:
        patch["notification_policy"] = {"channels": ["web"], "immediate": True}
    return TaskIntentResult(
        "update" if current_draft is not None else "create",
        patch=sanitize_patch(patch),
        confidence=0.85,
    )


def sanitize_patch(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    patch: dict[str, Any] = {}
    target = raw.get("target")
    if isinstance(target, str) and target.strip():
        patch["target"] = target.strip()[:300]
    frequency = raw.get("frequency_seconds")
    if isinstance(frequency, int) and not isinstance(frequency, bool):
        patch["frequency_seconds"] = frequency
    scope = raw.get("source_scope")
    if isinstance(scope, dict):
        urls = scope.get("urls", [])
        keywords = scope.get("keywords", [])
        if isinstance(urls, list) and isinstance(keywords, list):
            patch["source_scope"] = {
                "urls": [str(item) for item in urls if str(item).startswith(("http://", "https://"))],
                "keywords": [str(item).strip() for item in keywords if str(item).strip()],
            }
    condition = raw.get("trigger_condition")
    if isinstance(condition, dict):
        include = condition.get("must_contain", [])
        exclude = condition.get("must_not_contain", [])
        if isinstance(include, list) and isinstance(exclude, list):
            patch["trigger_condition"] = {
                "must_contain": [str(item) for item in include],
                "must_not_contain": [str(item) for item in exclude],
            }
    policy = raw.get("notification_policy")
    if isinstance(policy, dict) and isinstance(policy.get("channels"), list):
        channels = [
            str(item) for item in policy["channels"] if str(item) in {"feishu", "web"}
        ]
        if channels:
            patch["notification_policy"] = {
                "channels": list(dict.fromkeys(channels)),
                "immediate": bool(policy.get("immediate", True)),
            }
    return {key: value for key, value in patch.items() if key in _ALLOWED_PATCH_FIELDS}


def merge_task_patch(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    clean = sanitize_patch(patch)
    merged.update(clean)
    if "target" in clean and "source_scope" not in clean:
        merged["source_scope"] = {"urls": [], "keywords": [clean["target"]]}
    return merged


class ModelTaskIntentExtractor:
    def __init__(self, provider: Any, model_id: str) -> None:
        self.provider = provider
        self.model_id = model_id

    async def extract(
        self, text: str, current_draft: dict[str, Any] | None
    ) -> TaskIntentResult | None:
        system = (
            "你是任务意图解析器，只输出一个 JSON 对象，不要解释。"
            "intent 只能是 create/update/confirm/cancel/list/none。"
            "patch 只允许 target、source_scope、trigger_condition、frequency_seconds、"
            "notification_policy。时间间隔转换为秒；固定钟点或星期计划放到 clarification。"
            "target 只保留被关注对象，删除‘创建任务’、执行频率、汇报和通知等命令套话。"
            "用户纠正时只输出被明确修改的字段；‘不是X，是Y’必须采用Y。"
            "输出格式为 {\"intent\":\"create\",\"patch\":{},"
            "\"confidence\":0.0,\"clarification\":null}。"
            "不要执行任务，不要调用工具。"
        )
        prompt = json.dumps(
            {"message": text, "current_draft": current_draft or {}}, ensure_ascii=False
        )
        parts: list[str] = []
        async for chunk in self.provider.create_stream(
            self.model_id,
            [{"role": "user", "content": prompt}],
            system=system,
            temperature=0,
        ):
            if chunk.get("type") == "text_delta":
                parts.append(str(chunk.get("text", "")))
        result = self._parse_json("".join(parts))
        if result is None:
            return None
        intent = str(result.get("intent", "none"))
        if intent not in _ALLOWED_INTENTS:
            return None
        confidence_value = result.get("confidence", 0.8)
        confidence = float(confidence_value) if isinstance(confidence_value, (int, float)) else 0.8
        clarification = result.get("clarification") or result.get("clarification_question")
        return TaskIntentResult(
            intent=intent,
            patch=sanitize_patch(result.get("patch", {})),
            confidence=max(0.0, min(confidence, 1.0)),
            clarification=str(clarification).strip() if clarification else None,
        )

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any] | None:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None
