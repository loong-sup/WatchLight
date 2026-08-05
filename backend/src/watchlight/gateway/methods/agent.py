# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 agent 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway agent.* method handlers."""

import asyncio
import uuid
from typing import Any

from watchlight.agents.system_prompt.builder import DEFAULT_WATCHLIGHT_IDENTITY
from watchlight.contracts.agent.runtime import AgentEventType, AgentRunRequest
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient
from watchlight.gateway.websocket.frames import make_event


async def handle_agent(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    """Run a single agent turn, streaming events back to client."""
    runtime_obj = getattr(state, "_gateway_runtime_ref", None)
    if runtime_obj is None:
        return {"error": "no runtime"}

    rt = runtime_obj.runtime_registry.get()
    if rt is None:
        return {"error": "no agent runtime"}

    message = params.get("message", "")
    session_key = params.get("sessionKey", "main")
    run_id = str(uuid.uuid4())[:8]

    request = AgentRunRequest(
        run_id=run_id,
        session_key=session_key,
        provider_id=runtime_obj.default_provider,
        model_id=runtime_obj.default_model,
        system_prompt=DEFAULT_WATCHLIGHT_IDENTITY,
        user_message=message,
    )

    abort_signal = asyncio.Event()
    texts: list[str] = []

    async for event in rt.run(request, abort_signal):
        if event.type == AgentEventType.TEXT_DELTA and event.text:
            texts.append(event.text)
            await client.send_json(
                make_event(
                    "agent.event",
                    {
                        "type": "text_delta",
                        "sessionKey": session_key,
                        "text": event.text,
                    },
                )
            )
        elif event.type == AgentEventType.COMPLETE:
            await client.send_json(
                make_event(
                    "agent.event",
                    {
                        "type": "complete",
                        "sessionKey": session_key,
                    },
                )
            )

    return {"runId": run_id, "text": "".join(texts)}


async def handle_agent_wait(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    return await handle_agent(params, client, state)
