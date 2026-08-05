from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from watchlight.core.logging import get_logger
from watchlight.scheduler.presentation import (
    format_delete_candidates,
    format_delete_confirmation,
)

if TYPE_CHECKING:
    from watchlight.scheduler.service import TaskService

log = get_logger("scheduler.nl_delete")

DELETE_FLOW_TTL_SECONDS = 600
_DELETE_COMMANDS = {
    "删除任务",
    "删除关注任务",
    "我要删除任务",
    "我要删除关注任务",
    "帮我删除任务",
    "帮我删除关注任务",
}
_CANCEL_COMMANDS = {"取消", "取消删除"}

DeleteScope = tuple[str, str, str]


@dataclass(slots=True)
class DeleteConversation:
    candidate_ids: tuple[str, ...]
    selected_task_id: str | None
    expires_at: float


class NaturalLanguageDeleteFlow:
    """Deterministic, user-scoped task deletion flow with explicit confirmation."""

    def __init__(self, tasks: TaskService, ttl_seconds: int = DELETE_FLOW_TTL_SECONDS) -> None:
        self.tasks = tasks
        self.ttl_seconds = ttl_seconds
        self._pending: dict[DeleteScope, DeleteConversation] = {}

    def handle(
        self,
        user_id: str,
        channel: str,
        conversation_id: str,
        text: str,
        *,
        now: float | None = None,
    ) -> str | None:
        message = text.strip()
        current_time = time.monotonic() if now is None else now
        scope = (user_id, channel, conversation_id)

        if is_task_delete_intent(message):
            return self._start(scope, user_id, current_time)

        pending = self._pending.get(scope)
        if pending is None:
            if message == "确认删除":
                return "当前没有待确认删除的任务，请先发送“删除任务”。"
            return None

        if current_time >= pending.expires_at:
            del self._pending[scope]
            return "删除操作已超过 10 分钟并失效，请重新发送“删除任务”。"

        if message in _CANCEL_COMMANDS:
            del self._pending[scope]
            return "已取消删除，任务没有发生变化。"

        if pending.selected_task_id is not None:
            if message != "确认删除":
                return "尚未删除。请回复完整的“确认删除”执行，或回复“取消”放弃。"
            task_id = pending.selected_task_id
            del self._pending[scope]
            try:
                task = self.tasks.confirm_delete(user_id, task_id)
            except Exception as exc:
                log.error("watch_task_delete_failed", user_id=user_id, error=str(exc))
                return "删除任务时发生错误，未执行删除，请重新发起。"
            if task is None:
                return "任务状态已发生变化或不再可删除，本次删除未执行。"
            return (
                f"关注任务已进入删除流程：{task['target']}。"
                "系统将停止后续周期执行和通知，并在在途执行收敛后完成删除。"
            )

        if message == "确认删除":
            return "尚未选择唯一任务，请先回复任务名称关键词或完整任务 ID。"
        return self._select(scope, user_id, pending, message, current_time)

    def _start(self, scope: DeleteScope, user_id: str, now: float) -> str:
        try:
            tasks = self.tasks.list_deletable(user_id)
        except Exception as exc:
            log.error("watch_tasks_delete_list_failed", user_id=user_id, error=str(exc))
            self._pending.pop(scope, None)
            return "暂时无法查询可删除任务，请稍后重试。"
        if not tasks:
            self._pending.pop(scope, None)
            return "当前没有可删除的关注任务。"
        self._pending[scope] = DeleteConversation(
            candidate_ids=tuple(str(task["task_id"]) for task in tasks),
            selected_task_id=None,
            expires_at=now + self.ttl_seconds,
        )
        return format_delete_candidates(tasks)

    def _select(
        self,
        scope: DeleteScope,
        user_id: str,
        pending: DeleteConversation,
        message: str,
        now: float,
    ) -> str:
        if not message:
            return "请输入任务名称关键词或完整任务 ID。"
        try:
            current = self.tasks.list_deletable(user_id)
        except Exception as exc:
            log.error("watch_tasks_delete_match_failed", user_id=user_id, error=str(exc))
            return "暂时无法核对任务，请稍后重试或回复“取消”。"
        allowed_ids = set(pending.candidate_ids)
        candidates = [task for task in current if str(task["task_id"]) in allowed_ids]
        exact = [task for task in candidates if str(task["task_id"]) == message]
        if exact:
            matches = exact
        else:
            keyword = message.casefold()
            matches = [task for task in candidates if keyword in str(task["target"]).casefold()]

        if not matches:
            return "未在当前候选中找到匹配任务，请重新输入名称关键词或完整任务 ID。"
        if len(matches) > 1:
            pending.candidate_ids = tuple(str(task["task_id"]) for task in matches)
            pending.expires_at = now + self.ttl_seconds
            return format_delete_candidates(matches, narrowed=True)

        selected = matches[0]
        task_id = str(selected["task_id"])
        pending.candidate_ids = (task_id,)
        pending.selected_task_id = task_id
        pending.expires_at = now + self.ttl_seconds
        return format_delete_confirmation(selected)


def is_task_delete_intent(text: str) -> bool:
    return text.strip() in _DELETE_COMMANDS
