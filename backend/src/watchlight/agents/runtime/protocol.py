# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：定义可替换运行时协议。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""AgentRuntime Protocol — the replaceable execution engine interface."""

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol

from watchlight.contracts.agent.runtime import (
    AgentEvent,
    AgentRunRequest,
    CompactionResult,
)


class AgentRuntime(Protocol):
    """Replaceable agent execution engine.

    Implement this to swap the inference loop.
    """

    @property
    def runtime_id(self) -> str: ...

    def run(
        self,
        request: AgentRunRequest,
        abort_signal: asyncio.Event,
    ) -> AsyncIterator[AgentEvent]: ...

    async def compact(self, session_key: str, reason: str) -> CompactionResult | None: ...

    async def abort(self, run_id: str) -> None: ...

    async def dispose(self) -> None: ...
