from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from watchlight.core.logging import get_logger
from watchlight.scheduler.intent import (
    TaskIntentExtractor,
    TaskIntentResult,
    deterministic_intent,
    merge_task_patch,
)
from watchlight.scheduler.nl_delete import NaturalLanguageDeleteFlow
from watchlight.scheduler.normalize import normalize
from watchlight.scheduler.presentation import format_channel, format_frequency, format_task_list

if TYPE_CHECKING:
    from watchlight.scheduler.service import TaskService

log = get_logger("scheduler.nl")


@dataclass(slots=True)
class _Conversation:
    summary: dict[str, Any]
    rounds: int = 1
    task_id: str | None = None
    version_id: str | None = None


class NaturalLanguageTaskFlow:
    """Small, deterministic two-round task creation flow for chat channels."""

    def __init__(
        self, tasks: TaskService, intent_extractor: TaskIntentExtractor | None = None
    ) -> None:
        self.tasks = tasks
        self.intent_extractor = intent_extractor
        self.deletions = NaturalLanguageDeleteFlow(tasks)
        self._pending: dict[tuple[str, str, str], _Conversation] = {}

    def handle(
        self,
        user_id: str,
        channel: str,
        text: str,
        conversation_id: str | None = None,
        *,
        now: float | None = None,
    ) -> str | None:
        return self._handle(user_id, channel, text, conversation_id, now=now)

    async def handle_async(
        self,
        user_id: str,
        channel: str,
        text: str,
        conversation_id: str | None = None,
        *,
        now: float | None = None,
    ) -> str | None:
        conversation_key = conversation_id or ""
        key = (user_id, channel, conversation_key)
        current = self._pending.get(key)
        deterministic = deterministic_intent(
            text, current.summary if current is not None else None
        )
        if self.intent_extractor is None or deterministic.intent in {
            "confirm",
            "cancel",
            "none",
        } or deterministic.clarification:
            return self._handle(user_id, channel, text, conversation_id, now=now)
        try:
            extracted = await asyncio.wait_for(
                self.intent_extractor.extract(
                    text, current.summary if current is not None else None
                ),
                timeout=15,
            )
        except Exception as exc:
            log.warning("task_intent_model_fallback", error=str(exc))
            extracted = None
        if extracted is None or extracted.intent == "none":
            extracted = deterministic
        else:
            # 确定性提取负责显式时间、目标和渠道，模型用于补全更丰富的语义字段。
            # 让显式规则最后覆盖，避免模型把“不是五小时，是每天”改回旧值。
            combined_patch = merge_task_patch(extracted.patch, deterministic.patch)
            extracted = TaskIntentResult(
                intent=(
                    deterministic.intent
                    if deterministic.intent in {"create", "update"}
                    else extracted.intent
                ),
                patch=combined_patch,
                confidence=extracted.confidence,
                clarification=extracted.clarification or deterministic.clarification,
            )
        return self._handle(
            user_id,
            channel,
            text,
            conversation_id,
            now=now,
            extracted=extracted,
        )

    def _handle(
        self,
        user_id: str,
        channel: str,
        text: str,
        conversation_id: str | None = None,
        *,
        now: float | None = None,
        extracted: TaskIntentResult | None = None,
    ) -> str | None:
        conversation_key = conversation_id or ""
        deletion_reply = self.deletions.handle(
            user_id,
            channel,
            conversation_key,
            text,
            now=now,
        )
        if deletion_reply is not None:
            return deletion_reply

        key = (user_id, channel, conversation_key)
        message = text.strip()
        if is_task_list_intent(message):
            try:
                return format_task_list(self.tasks.list(user_id))
            except Exception as exc:
                log.error("watch_tasks_list_failed", user_id=user_id, error=str(exc))
                return "暂时无法查询关注任务，请稍后重试。"

        pending = self._pending.get(key)
        if pending and message in {"确认", "确认创建", "确定"}:
            if not pending.task_id or not pending.version_id:
                return "信息尚未补齐，暂时不能确认。请按表单创建关注任务。"
            task = self.tasks.confirm(user_id, pending.task_id, pending.version_id)
            del self._pending[key]
            return f"关注任务已创建并启用：{task['target']}"

        intent = extracted or deterministic_intent(
            message, pending.summary if pending is not None else None
        )
        if intent.intent == "cancel" and pending is not None:
            del self._pending[key]
            return "已取消创建关注任务。"
        if intent.clarification:
            return intent.clarification
        if pending is None and intent.intent != "create":
            return None

        if pending is None:
            pending = _Conversation({})
            self._pending[key] = pending
        else:
            pending.rounds += 1
        pending.summary = merge_task_patch(pending.summary, intent.patch)

        frequency = pending.summary.get("frequency_seconds")
        if isinstance(frequency, int) and not 900 <= frequency <= 604800:
            return "执行间隔必须在 15 分钟到 7 天之间，请重新说明执行频率。"

        normalized = normalize(pending.summary)
        if normalized.unsupported_reason:
            del self._pending[key]
            return f"该请求不受支持：{normalized.unsupported_reason}"
        if normalized.missing_fields:
            if pending.rounds >= 2:
                del self._pending[key]
                return "两轮内仍未补齐信息，请改用任务表单。缺少：" + "、".join(
                    normalized.missing_fields
                )
            return "请补充：" + "、".join(normalized.missing_fields)

        if pending.task_id:
            task = self.tasks.update(user_id, pending.task_id, normalized.summary)
            pending.summary = normalized.summary
            pending.version_id = str(task["current_version_id"])
        else:
            created = self.tasks.create(user_id, normalized.summary)
            if created.error:
                del self._pending[key]
                return f"无法创建关注任务：{created.error}"
            pending.summary = created.normalized_summary
            pending.task_id = created.task_id
            pending.version_id = created.normalized_version_id
        return format_task_confirmation(pending.summary)


def format_task_confirmation(summary: dict[str, Any]) -> str:
    """Render internal normalized fields as a user-facing Markdown confirmation."""
    source_scope = summary.get("source_scope")
    sources = source_scope if isinstance(source_scope, dict) else {}
    urls = [str(item) for item in sources.get("urls", [])]
    keywords = [str(item) for item in sources.get("keywords", [])]
    source_lines = [f"- 指定页面：{url}" for url in urls]
    source_lines.extend(f"- 公开网络关键词：{keyword}" for keyword in keywords)
    if not source_lines:
        source_lines.append("- 未指定")

    condition = summary.get("trigger_condition")
    conditions = condition if isinstance(condition, dict) else {}
    must_contain = [str(item) for item in conditions.get("must_contain", [])]
    must_not_contain = [str(item) for item in conditions.get("must_not_contain", [])]
    condition_lines = [f"- 包含：{'、'.join(must_contain)}"] if must_contain else []
    if must_not_contain:
        condition_lines.append(f"- 排除：{'、'.join(must_not_contain)}")
    if not condition_lines:
        condition_lines.append("- 检测到实质内容变化")

    policy = summary.get("notification_policy")
    notification = policy if isinstance(policy, dict) else {}
    channels = [format_channel(str(item)) for item in notification.get("channels", [])]
    frequency = format_frequency(int(summary.get("frequency_seconds", 0)))
    return "\n".join(
        [
            "## 请确认创建关注任务",
            "",
            f"**关注目标**：{summary.get('target', '未指定')}",
            "",
            "**来源范围**",
            *source_lines,
            "",
            "**触发条件**",
            *condition_lines,
            "",
            f"**执行频率**：{frequency}",
            f"**通知渠道**：{'、'.join(channels) or '未指定'}",
            f"**无变化时通知**：{'是' if notification.get('report_on_no_change') else '否'}",
            "",
            "回复 **“确认”** 后才会启用。",
        ]
    )


def is_task_list_intent(text: str) -> bool:
    message = text.strip()
    has_task_subject = "任务" in message or "关注" in message
    query_markers = (
        "哪些",
        "有什么",
        "列表",
        "查看",
        "查询",
        "多少",
        "目前",
        "当前",
        "之前",
        "以前",
        "还在",
        "创建了",
    )
    return has_task_subject and any(marker in message for marker in query_markers)
