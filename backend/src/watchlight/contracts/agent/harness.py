# 文件说明：本文件属于 契约层。
# 主要职责：实现 harness 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""AgentHarness Protocol — lifecycle management for agent execution.

Matches TS AgentHarness in src/agents/harness/types.ts.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AgentHarnessSupport:
    supported: bool
    priority: int = 0


@dataclass
class AgentHarnessAttemptParams:
    run_id: str
    session_key: str
    provider: str
    model_id: str
    system_prompt: str
    user_message: str
    timeout_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentHarnessAttemptResult:
    aborted: bool = False
    timed_out: bool = False
    assistant_texts: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    compaction_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentHarnessSupportContext:
    provider: str
    model_id: str


class AgentHarness(Protocol):
    """Lifecycle wrapper around an AgentRuntime."""

    @property
    def id(self) -> str: ...

    @property
    def label(self) -> str: ...

    def supports(self, ctx: AgentHarnessSupportContext) -> AgentHarnessSupport: ...

    async def run_attempt(self, params: AgentHarnessAttemptParams) -> AgentHarnessAttemptResult: ...

    async def compact(self, session_key: str, reason: str) -> dict[str, Any] | None: ...

    async def reset(self, session_key: str) -> None: ...

    async def dispose(self) -> None: ...
