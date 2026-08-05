# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：处理入口请求并转交核心链路。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Main WebSocket connection handler — uses unified error middleware."""

from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from watchlight.contracts.protocol.frames import RequestFrame, ResponseFrame
from watchlight.core.logging import get_logger
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient
from watchlight.gateway.websocket.error_handler import dispatch_method
from watchlight.gateway.websocket.frames import make_response, parse_frame
from watchlight.gateway.websocket.handshake import perform_handshake
from watchlight.gateway.websocket.heartbeat import TickEmitter

log = get_logger("gateway.ws")

MethodHandler = Any


async def handle_websocket(
    ws: WebSocket,
    state: GatewayRuntimeState,
    method_registry: dict[str, MethodHandler],
) -> None:
    """Handle a single WebSocket connection lifecycle."""
    await ws.accept()
    client = GatewayWsClient(ws=ws)
    tick = TickEmitter()

    try:
        # Wait for connect handshake
        raw = await ws.receive_json()
        frame = parse_frame(raw)

        if not isinstance(frame, RequestFrame) or frame.method != "connect":
            frame_id = frame.id if isinstance(frame, (RequestFrame, ResponseFrame)) else "?"
            await client.send_json(
                make_response(
                    frame_id,
                    False,
                    error={"code": "INVALID_REQUEST", "message": "First message must be connect"},
                )
            )
            return

        hello_ok = perform_handshake(frame.params or {}, client, state)
        await client.send_json(make_response(frame.id, True, payload=hello_ok))

        # Register client + bump state version
        state.connected_clients[client.conn_id] = client
        state.state_version = state.state_version.model_copy(
            update={"presence": state.state_version.presence + 1}
        )

        # Start heartbeat
        tick.start(client.send_json)

        # Main message loop — uses unified error handler
        while True:
            raw = await ws.receive_json()
            frame = parse_frame(raw)

            if not isinstance(frame, RequestFrame):
                continue

            handler = method_registry.get(frame.method)
            if handler is None:
                await client.send_json(
                    make_response(
                        frame.id,
                        False,
                        error={
                            "code": "METHOD_NOT_FOUND",
                            "message": f"Unknown method: {frame.method}",
                        },
                    )
                )
                continue

            # Unified dispatch with error handling
            response = await dispatch_method(
                handler, frame.id, frame.method, frame.params or {}, client, state
            )
            await client.send_json(response)

    except WebSocketDisconnect:
        log.info("ws_disconnected", conn_id=client.conn_id)
    except Exception as e:
        log.error("ws_error", conn_id=client.conn_id, error=str(e))
    finally:
        tick.stop()
        state.connected_clients.pop(client.conn_id, None)
        state.state_version = state.state_version.model_copy(
            update={"presence": max(0, state.state_version.presence - 1)}
        )
