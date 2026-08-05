# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：集中定义类型和数据结构。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Subagent types."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpawnParams:
    task: str
    model: str | None = None
    workspace: str | None = None
    cleanup: str = "delete"  # "delete" | "keep"
    timeout_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubagentRunRecord:
    run_id: str
    child_session_key: str
    requester_session_key: str
    task: str
    cleanup: str = "delete"
    model: str | None = None
    created_at: int = 0
    started_at: int | None = None
    ended_at: int | None = None
    outcome: str | None = None  # "completed" | "failed" | "killed" | "timeout"
    result_text: str | None = None
    spawn_depth: int = 0
