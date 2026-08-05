# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 retry loop 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Retry loop — the outer execution engine with classified error recovery."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from watchlight.agents.runtime.embedded.auth_rotation import AuthProfileRotator
from watchlight.agents.runtime.embedded.error_classifier import classify_error
from watchlight.contracts.agent.runtime import (
    AgentEvent,
    AgentEventType,
    AgentRunRequest,
)
from watchlight.core.logging import get_logger

log = get_logger("agent.retry_loop")

MAX_OVERFLOW_COMPACTION_ATTEMPTS = 3
MAX_TIMEOUT_COMPACTION_ATTEMPTS = 2


class RetryLoopResult:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []
        self.iterations: int = 0
        self.compaction_count: int = 0
        self.fallback_used: bool = False


async def run_with_retry(
    run_fn: Any,
    request: AgentRunRequest,
    abort_signal: asyncio.Event,
    compact_fn: Any | None = None,
    fallback_model: str | None = None,
    auth_rotator: AuthProfileRotator | None = None,
) -> AsyncIterator[AgentEvent]:
    """Wrap a run function with the full retry loop.

    Args:
        run_fn: async generator function (request, abort) -> AsyncIterator[AgentEvent]
        request: The agent run request.
        abort_signal: Signal to abort the run.
        compact_fn: Optional async function(session_key, reason) -> CompactionResult
        fallback_model: Optional fallback model ID.
        auth_rotator: Optional auth profile rotator.
    """
    max_iterations = auth_rotator.max_iterations() if auth_rotator else 32
    overflow_compaction_attempts = 0
    timeout_compaction_attempts = 0
    iteration = 0
    current_model = request.model_id

    while iteration < max_iterations:
        if abort_signal.is_set():
            yield AgentEvent(type=AgentEventType.COMPLETE, metadata={"aborted": True})
            return

        iteration += 1
        attempt_error: str | None = None
        attempt_events: list[AgentEvent] = []

        try:
            # Update model if changed by fallback
            request.model_id = current_model

            async for event in run_fn(request, abort_signal):
                if event.type == AgentEventType.ERROR:
                    attempt_error = event.error
                    attempt_events.append(event)
                else:
                    yield event
                    attempt_events.append(event)

            # If we got a COMPLETE event without error, success
            if any(e.type == AgentEventType.COMPLETE for e in attempt_events) and not attempt_error:
                return

        except Exception as e:
            attempt_error = str(e)
            log.error("retry_attempt_error", iteration=iteration, error=attempt_error[:200])

        if not attempt_error:
            return  # Success

        # Classify and recover
        error_class = classify_error(attempt_error)
        log.info(
            "retry_classified",
            iteration=iteration,
            error_class=error_class,
            error=attempt_error[:100],
        )

        if error_class == "context_overflow":
            if overflow_compaction_attempts < MAX_OVERFLOW_COMPACTION_ATTEMPTS and compact_fn:
                log.info("retry_compact_overflow", attempt=overflow_compaction_attempts + 1)
                try:
                    await compact_fn(request.session_key, "overflow")
                except Exception as ce:
                    log.error("retry_compact_failed", error=str(ce))
                overflow_compaction_attempts += 1
                continue

        elif error_class == "timeout":
            if timeout_compaction_attempts < MAX_TIMEOUT_COMPACTION_ATTEMPTS and compact_fn:
                log.info("retry_compact_timeout", attempt=timeout_compaction_attempts + 1)
                try:
                    await compact_fn(request.session_key, "timeout")
                except Exception as ce:
                    log.error("retry_compact_failed", error=str(ce))
                timeout_compaction_attempts += 1
                continue

        elif error_class == "auth":
            if auth_rotator and auth_rotator.rotate("auth"):
                continue

        elif error_class in ("rate_limit", "overloaded"):
            # Try rotating auth profile first
            if auth_rotator and auth_rotator.rotate(error_class):
                await asyncio.sleep(1)  # Brief backoff
                continue
            # Then try fallback model
            if fallback_model and current_model != fallback_model:
                log.info("retry_fallback_model", from_model=current_model, to_model=fallback_model)
                current_model = fallback_model
                continue

        elif error_class == "model_not_found":
            if fallback_model and current_model != fallback_model:
                log.info("retry_fallback_model", from_model=current_model, to_model=fallback_model)
                current_model = fallback_model
                continue

        elif error_class == "billing":
            # Billing errors are not retryable
            yield AgentEvent(type=AgentEventType.ERROR, error=attempt_error)
            return

        # Unknown or exhausted retries for this class
        if error_class == "unknown" or iteration >= max_iterations - 1:
            yield AgentEvent(type=AgentEventType.ERROR, error=attempt_error)
            return

        # Generic retry with backoff
        await asyncio.sleep(min(iteration * 0.5, 5))

    yield AgentEvent(
        type=AgentEventType.ERROR, error=f"Retry limit exhausted after {iteration} iterations"
    )
