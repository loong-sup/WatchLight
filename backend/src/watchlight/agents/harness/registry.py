# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Harness registry — select harness by provider/model."""

from watchlight.agents.harness.types import (
    AgentHarness,
    AgentHarnessSupportContext,
)


class HarnessRegistry:
    def __init__(self) -> None:
        self._harnesses: dict[str, AgentHarness] = {}

    def register(self, harness: AgentHarness) -> None:
        self._harnesses[harness.id] = harness

    def get(self, harness_id: str) -> AgentHarness | None:
        return self._harnesses.get(harness_id)

    def select(self, ctx: AgentHarnessSupportContext) -> AgentHarness | None:
        best: AgentHarness | None = None
        best_priority = -1
        for harness in self._harnesses.values():
            support = harness.supports(ctx)
            if support.supported and support.priority > best_priority:
                best = harness
                best_priority = support.priority
        return best

    def list(self) -> list[str]:
        return list(self._harnesses.keys())
