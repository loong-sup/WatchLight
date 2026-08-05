# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：集中定义类型和数据结构。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Re-export harness types from contracts."""

from watchlight.contracts.agent.harness import (
    AgentHarness,
    AgentHarnessAttemptParams,
    AgentHarnessAttemptResult,
    AgentHarnessSupport,
    AgentHarnessSupportContext,
)

__all__ = [
    "AgentHarness",
    "AgentHarnessAttemptParams",
    "AgentHarnessAttemptResult",
    "AgentHarnessSupport",
    "AgentHarnessSupportContext",
]
