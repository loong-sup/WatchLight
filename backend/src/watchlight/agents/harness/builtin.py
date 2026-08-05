# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 builtin 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Built-in harness that delegates to an AgentRuntime."""

import asyncio
from typing import Any

from watchlight.agents.harness.types import (
    AgentHarnessAttemptParams,
    AgentHarnessAttemptResult,
    AgentHarnessSupport,
    AgentHarnessSupportContext,
)
from watchlight.agents.runtime.protocol import AgentRuntime
from watchlight.contracts.agent.runtime import AgentEventType, AgentRunRequest


class BuiltinHarness:
    """Default harness — wraps an AgentRuntime."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    @property
    def id(self) -> str:
        return f"builtin-{self._runtime.runtime_id}"

    @property
    def label(self) -> str:
        return f"Built-in ({self._runtime.runtime_id})"

    def supports(self, ctx: AgentHarnessSupportContext) -> AgentHarnessSupport:
        return AgentHarnessSupport(supported=True, priority=0)

    async def run_attempt(self, params: AgentHarnessAttemptParams) -> AgentHarnessAttemptResult:
        abort_signal = asyncio.Event()
        request = AgentRunRequest(
            run_id=params.run_id,
            session_key=params.session_key,
            provider_id=params.provider,
            model_id=params.model_id,
            system_prompt=params.system_prompt,
            user_message=params.user_message,
            timeout_ms=params.timeout_ms,
        )

        texts: list[str] = []
        input_tokens = 0
        output_tokens = 0
        aborted = False

        async for event in self._runtime.run(request, abort_signal):
            if event.type == AgentEventType.TEXT_DELTA and event.text:
                texts.append(event.text)
            elif event.type == AgentEventType.USAGE:
                input_tokens += event.input_tokens
                output_tokens += event.output_tokens
            elif event.type == AgentEventType.COMPLETE:
                aborted = event.metadata.get("aborted", False)

        return AgentHarnessAttemptResult(
            aborted=aborted,
            assistant_texts=texts,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    async def compact(self, session_key: str, reason: str) -> dict[str, Any] | None:
        result = await self._runtime.compact(session_key, reason)
        if result:
            return {
                "messagesBefore": result.messages_before,
                "messagesAfter": result.messages_after,
            }
        return None

    async def reset(self, session_key: str) -> None:
        pass

    async def dispose(self) -> None:
        await self._runtime.dispose()
