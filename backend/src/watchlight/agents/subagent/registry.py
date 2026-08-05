# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Subagent registry — track running and completed subagents."""

import time

from watchlight.agents.subagent.types import SubagentRunRecord
from watchlight.core.logging import get_logger

log = get_logger("agent.subagent.registry")


class SubagentRegistry:
    def __init__(self) -> None:
        self._records: dict[str, SubagentRunRecord] = {}

    def register(self, record: SubagentRunRecord) -> None:
        self._records[record.run_id] = record
        log.info("subagent_registered", run_id=record.run_id, task=record.task[:50])

    def get(self, run_id: str) -> SubagentRunRecord | None:
        return self._records.get(run_id)

    def list_active(self) -> list[SubagentRunRecord]:
        return [r for r in self._records.values() if r.outcome is None]

    def list_completed(self) -> list[SubagentRunRecord]:
        return [r for r in self._records.values() if r.outcome is not None]

    def complete(self, run_id: str, outcome: str, result_text: str | None = None) -> None:
        record = self._records.get(run_id)
        if record:
            record.outcome = outcome
            record.ended_at = int(time.time() * 1000)
            record.result_text = result_text
            log.info("subagent_completed", run_id=run_id, outcome=outcome)
