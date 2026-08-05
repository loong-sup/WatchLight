# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 lifecycle 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Subagent lifecycle management."""

from watchlight.agents.subagent.registry import SubagentRegistry
from watchlight.core.logging import get_logger

log = get_logger("agent.subagent.lifecycle")


def kill_subagent(registry: SubagentRegistry, run_id: str) -> bool:
    record = registry.get(run_id)
    if record and record.outcome is None:
        registry.complete(run_id, "killed")
        return True
    return False


def kill_all_active(registry: SubagentRegistry) -> int:
    killed = 0
    for record in registry.list_active():
        registry.complete(record.run_id, "killed")
        killed += 1
    return killed
