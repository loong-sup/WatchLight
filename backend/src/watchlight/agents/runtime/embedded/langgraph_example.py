# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 langgraph example 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Example: Custom AgentRuntime using LangGraph.

This is a reference implementation showing how to implement the AgentRuntime Protocol
with a different execution engine. To use:

    runtime_registry.register(LangGraphRuntime(), default=False)
    # Then in config: agents.defaults.runtime = "langgraph"

Requires: pip install langgraph langchain-core
"""

import asyncio
from collections.abc import AsyncIterator

from watchlight.contracts.agent.runtime import (
    AgentEvent,
    AgentEventType,
    AgentRunRequest,
    CompactionResult,
)


class LangGraphRuntime:
    """Example AgentRuntime backed by LangGraph.

    This demonstrates the Protocol pattern — any class implementing
    runtime_id, run(), compact(), abort(), dispose() can be a runtime.
    """

    runtime_id = "langgraph"

    async def run(
        self,
        request: AgentRunRequest,
        abort_signal: asyncio.Event,
    ) -> AsyncIterator[AgentEvent]:
        """Execute using LangGraph (placeholder — needs langgraph installed)."""
        try:
            # Attempt to import langgraph
            from langchain_core.messages import HumanMessage  # type: ignore[import-not-found]
            from langgraph.graph import StateGraph  # type: ignore[import-not-found]

            _ = (HumanMessage, StateGraph)

            # Build a simple LangGraph
            # ... (actual implementation depends on your graph definition)

            yield AgentEvent(
                type=AgentEventType.TEXT_DELTA,
                text=f"[LangGraph] Processing: {request.user_message}",
            )
            yield AgentEvent(type=AgentEventType.COMPLETE)

        except ImportError:
            yield AgentEvent(
                type=AgentEventType.TEXT_DELTA,
                text="[LangGraph runtime not available — install langgraph + langchain-core]",
            )
            yield AgentEvent(type=AgentEventType.COMPLETE)

    async def compact(self, session_key: str, reason: str) -> CompactionResult | None:
        return None

    async def abort(self, run_id: str) -> None:
        pass

    async def dispose(self) -> None:
        pass
