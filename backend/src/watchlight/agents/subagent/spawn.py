# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 spawn 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Subagent spawning — create child agents."""

import asyncio
import time
import uuid
from typing import Any

from watchlight.agents.subagent.depth import check_depth
from watchlight.agents.subagent.registry import SubagentRegistry
from watchlight.agents.subagent.types import SpawnParams, SubagentRunRecord
from watchlight.contracts.agent.runtime import AgentEventType, AgentRunRequest
from watchlight.core.logging import get_logger

log = get_logger("agent.subagent.spawn")


async def spawn_subagent(
    params: SpawnParams,
    parent_session_key: str,
    parent_depth: int,
    runtime: Any,
    registry: SubagentRegistry,
) -> SubagentRunRecord:
    """Spawn a child agent to execute a task."""
    check_depth(parent_depth)

    run_id = str(uuid.uuid4())[:8]
    child_key = f"subagent:{parent_session_key}:{run_id}"

    record = SubagentRunRecord(
        run_id=run_id,
        child_session_key=child_key,
        requester_session_key=parent_session_key,
        task=params.task,
        cleanup=params.cleanup,
        model=params.model,
        created_at=int(time.time() * 1000),
        spawn_depth=parent_depth + 1,
    )
    registry.register(record)

    # Run the child agent
    record.started_at = int(time.time() * 1000)

    request = AgentRunRequest(
        run_id=run_id,
        session_key=child_key,
        provider_id="dashscope",
        model_id=params.model or "qwen-max",
        system_prompt="You are a helpful subagent. Complete the assigned task.",
        user_message=params.task,
    )

    abort = asyncio.Event()
    result_parts: list[str] = []
    try:
        async for event in runtime.run(request, abort):
            if event.type == AgentEventType.TEXT_DELTA and event.text:
                result_parts.append(event.text)
        registry.complete(run_id, "completed", "".join(result_parts))
    except Exception as e:
        log.error("subagent_failed", run_id=run_id, error=str(e))
        registry.complete(run_id, "failed", str(e))

    return record
