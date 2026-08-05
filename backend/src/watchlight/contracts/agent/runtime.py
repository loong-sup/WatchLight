# 文件说明：本文件属于 契约层。
# 主要职责：实现 runtime 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""AgentRuntime Protocol — the replaceable execution engine.

This is the core abstraction that makes the agent runtime pluggable.
Implement this Protocol to swap the entire inference engine.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


# revision: 0eId9 0dT85
class AgentEventType(StrEnum):
    TEXT_DELTA = "text_delta"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"
    REASONING = "reasoning"
    USAGE = "usage"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class AgentEvent:
    type: AgentEventType
    text: str | None = None
    tool_name: str | None = None
    tool_params: dict[str, Any] | None = None
    tool_result: Any | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunRequest:
    run_id: str
    session_key: str
    provider_id: str
    model_id: str
    system_prompt: str
    user_message: str
    history: list[dict[str, Any]] = field(default_factory=list)
    timeout_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactionResult:
    messages_before: int
    messages_after: int
    summary: str | None = None


class AgentRuntime(Protocol):
    """Replaceable agent execution engine.

    Implement this to swap the inference loop (e.g., LangGraph, AutoGen, custom).
    """

    @property
    def runtime_id(self) -> str: ...

    def run(
        self,
        request: AgentRunRequest,
        abort_signal: asyncio.Event,
    ) -> AsyncIterator[AgentEvent]: ...

    async def compact(
        self,
        session_key: str,
        reason: str,
    ) -> CompactionResult | None: ...

    async def abort(self, run_id: str) -> None: ...

    async def dispose(self) -> None: ...
