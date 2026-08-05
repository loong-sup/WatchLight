# 文件说明：本文件属于 通道接入层。
# 主要职责：处理入口请求并转交核心链路。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""WebChat gateway method handlers — chat.send, chat.history, chat.abort."""

import asyncio
import uuid
from typing import Any

from watchlight.agents.system_prompt.builder import DEFAULT_WATCHLIGHT_IDENTITY
from watchlight.contracts.agent.runtime import AgentEventType, AgentRunRequest
from watchlight.core.logging import get_logger
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient
from watchlight.gateway.websocket.frames import make_event

log = get_logger("channel.webchat")


async def handle_chat_send(
    params: dict[str, Any],
    client: GatewayWsClient,
    state: GatewayRuntimeState,
) -> dict[str, Any]:
    """Handle chat.send — route message to agent, stream response back."""
    message = params.get("message", "")
    session_key = params.get("sessionKey", "main")
    run_id = str(uuid.uuid4())[:8]

    # Get runtime from app state (injected later in Phase 6 wiring)
    runtime = getattr(state, "runtime", None)
    if runtime is None:
        # Mock response for now
        await client.send_json(
            make_event(
                "agent.event",
                {
                    "type": "text_delta",
                    "sessionKey": session_key,
                    "text": f"[mock] Echo: {message}",
                },
            )
        )
        await client.send_json(
            make_event(
                "agent.event",
                {
                    "type": "complete",
                    "sessionKey": session_key,
                },
            )
        )
        return {"runId": run_id, "sessionKey": session_key}

    # Real runtime path
    abort_signal = asyncio.Event()
    request = AgentRunRequest(
        run_id=run_id,
        session_key=session_key,
        provider_id="mock",
        model_id="mock",
        system_prompt=DEFAULT_WATCHLIGHT_IDENTITY,
        user_message=message,
    )

    async for event in runtime.run(request, abort_signal):
        if event.type == AgentEventType.TEXT_DELTA and event.text:
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

    return {"runId": run_id, "sessionKey": session_key}


async def handle_chat_history(
    params: dict[str, Any],
    client: GatewayWsClient,
    state: GatewayRuntimeState,
) -> dict[str, Any]:
    """Handle chat.history — return session transcript."""
    return {"messages": [], "sessionKey": params.get("sessionKey", "main")}


async def handle_chat_abort(
    params: dict[str, Any],
    client: GatewayWsClient,
    state: GatewayRuntimeState,
) -> dict[str, Any]:
    """Handle chat.abort."""
    return {"ok": True}
