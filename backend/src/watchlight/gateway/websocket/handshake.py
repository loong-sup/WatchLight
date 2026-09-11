# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 handshake 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""WebSocket connect handshake."""

from typing import Any

from watchlight.contracts.protocol.hello import ConnectParams
from watchlight.contracts.protocol.version import PROTOCOL_VERSION
from watchlight.core.errors import ProtocolError
from watchlight.gateway.constants import (
    DEFAULT_MAX_BUFFERED_BYTES,
    DEFAULT_MAX_PAYLOAD,
    DEFAULT_TICK_INTERVAL_MS,
)
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient


def perform_handshake(
    params: dict[str, Any],
    client: GatewayWsClient,
    state: GatewayRuntimeState,
    server_version: str = "0.1.0",
    supported_methods: list[str] | None = None,
    supported_events: list[str] | None = None,
) -> dict[str, Any]:
    """Validate connect params and build HelloOk response."""
    connect = ConnectParams.model_validate(params)

    # Protocol version negotiation
    if connect.max_protocol < 1 or connect.min_protocol > PROTOCOL_VERSION:
        raise ProtocolError(
            f"Protocol version mismatch: client [{connect.min_protocol}-{connect.max_protocol}], "
            f"server [{PROTOCOL_VERSION}]"
        )

    negotiated = min(connect.max_protocol, PROTOCOL_VERSION)

    # Store client info
    client.client_info = connect.client.model_dump(by_alias=True)
    client.authenticated = True

    methods = supported_methods or [
        "connect",
        "config.get",
        "config.set",
        "config.apply",
        "config.patch",
        "sessions.list",
        "sessions.create",
        "sessions.send",
        "sessions.abort",
        "sessions.patch",
        "sessions.reset",
        "sessions.delete",
        "sessions.compact",
        "sessions.preview",
        "sessions.archive",
        "agent",
        "agent.wait",
        "agent.identity.get",
        "channels.status",
        "tools.catalog",
        "tools.effective",
        "models.list",
        "commands.list",
    ]
    events = supported_events or [
        "tick",
        "shutdown",
        "sessions.changed",
        "agent.event",
        "runtime.event",
    ]

    hello_ok: dict[str, Any] = {
        "type": "hello-ok",
        "protocol": negotiated,
        "server": {"version": server_version, "connId": client.conn_id},
        "features": {"methods": methods, "events": events},
        "snapshot": state.build_snapshot(),
        "policy": {
            "maxPayload": DEFAULT_MAX_PAYLOAD,
            "maxBufferedBytes": DEFAULT_MAX_BUFFERED_BYTES,
            "tickIntervalMs": DEFAULT_TICK_INTERVAL_MS,
        },
    }
    return hello_ok
