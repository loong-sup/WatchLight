from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class TaskView(TypedDict):
    task_id: str
    target: str
    status: str
    status_label: str
    frequency_seconds: int
    frequency_label: str
    notification_channels: list[str]
    notification_channel_labels: list[str]


_STATUS_LABELS = {
    "active": "已启用",
    "paused": "已暂停",
    "draining": "删除中",
    "deleted": "已删除",
}
_CHANNEL_LABELS = {"feishu": "飞书", "web": "Web", "webchat": "Web"}


def format_frequency(seconds: int) -> str:
    if seconds == 3600:
        return "每小时"
    if seconds == 86400:
        return "每天"
    if seconds and seconds % 86400 == 0:
        return f"每 {seconds // 86400} 天"
    if seconds and seconds % 3600 == 0:
        return f"每 {seconds // 3600} 小时"
    if seconds and seconds % 60 == 0:
        return f"每 {seconds // 60} 分钟"
    return f"每 {seconds} 秒" if seconds else "未指定"


def format_channel(channel: str) -> str:
    return _CHANNEL_LABELS.get(channel, channel)


def task_to_view(task: Mapping[str, Any]) -> TaskView:
    frequency_seconds = int(task["frequency_seconds"])
    status = str(task["status"])
    channels = _notification_channels(task.get("notification_policy_json"))
    return {
        "task_id": str(task["task_id"]),
        "target": str(task["target"]),
        "status": status,
        "status_label": _STATUS_LABELS.get(status, status),
        "frequency_seconds": frequency_seconds,
        "frequency_label": format_frequency(frequency_seconds),
        "notification_channels": channels,
        "notification_channel_labels": [format_channel(channel) for channel in channels],
    }


def format_task_list(tasks: Sequence[Mapping[str, Any]]) -> str:
    if not tasks:
        return "当前没有关注任务。"

    lines = [f"## 当前关注任务（{len(tasks)}）", ""]
    for index, task in enumerate(tasks, start=1):
        view = task_to_view(task)
        channels = "、".join(view["notification_channel_labels"]) or "未指定"
        lines.extend(
            [
                f"### {index}. {view['target']}",
                f"- 状态：{view['status_label']}（{view['status']}）",
                f"- 执行频率：{view['frequency_label']}",
                f"- 通知渠道：{channels}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def format_delete_candidates(
    tasks: Sequence[Mapping[str, Any]], *, narrowed: bool = False
) -> str:
    title = "## 匹配到多个可删除任务" if narrowed else "## 可删除的关注任务"
    lines = [title, ""]
    for task in tasks:
        view = task_to_view(task)
        lines.extend(
            [
                f"### {view['target']}",
                f"- 状态：{view['status_label']}（{view['status']}）",
                f"- 任务 ID：`{view['task_id']}`",
                "",
            ]
        )
    if narrowed:
        lines.append("请继续回复更精确的任务名称关键词，或回复上方完整任务 ID。")
    else:
        lines.append("请回复要删除任务的**名称关键词**，或回复上方完整任务 ID。")
    lines.append("输入序号不会执行删除。")
    return "\n".join(lines)


def format_delete_confirmation(task: Mapping[str, Any]) -> str:
    view = task_to_view(task)
    return "\n".join(
        [
            "## 请确认删除关注任务",
            "",
            f"**任务名称**：{view['target']}",
            f"**任务 ID**：`{view['task_id']}`",
            f"**当前状态**：{view['status_label']}（{view['status']}）",
            "",
            "删除后将停止该任务后续的周期执行和通知；已提交的删除不能在对话中撤销。",
            "",
            "回复 **“确认删除”** 执行，或回复 **“取消”** 放弃。",
        ]
    )


def _notification_channels(raw_policy: Any) -> list[str]:
    try:
        policy = json.loads(str(raw_policy)) if isinstance(raw_policy, str) else raw_policy
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(policy, dict):
        return []
    raw_channels = policy.get("channels")
    if not isinstance(raw_channels, list):
        return []
    return [str(channel) for channel in raw_channels]
