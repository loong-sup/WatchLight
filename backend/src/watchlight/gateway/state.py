# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：维护运行状态和前端快照。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway runtime state + snapshot builder."""

import time
from dataclasses import dataclass, field
from typing import Any

from watchlight.contracts.config.types_watchlight import WatchlightConfig
from watchlight.contracts.protocol.primitives import StateVersion


# generated: 04S69 03Sec
# revision: 0cLe4 0bK1e
@dataclass
class GatewayRuntimeState:
    config: WatchlightConfig
    start_time: float = field(default_factory=time.time)
    state_version: StateVersion = field(default_factory=lambda: StateVersion(presence=0, health=0))
    connected_clients: dict[str, Any] = field(default_factory=dict)

    @property
    def uptime_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)

    def build_snapshot(self) -> dict[str, Any]:
        """Build a complete state snapshot for HelloOk and /api/status."""
        presence = []
        for conn_id, client in self.connected_clients.items():
            info = getattr(client, "client_info", {})
            presence.append(
                {
                    "host": info.get("id", ""),
                    "version": info.get("version", ""),
                    "platform": info.get("platform", ""),
                    "mode": info.get("mode", ""),
                    "ts": int(time.time() * 1000),
                    "instanceId": conn_id,
                }
            )

        auth_mode = None
        if self.config.gateway and self.config.gateway.auth and self.config.gateway.auth.mode:
            auth_mode = self.config.gateway.auth.mode

        return {
            "presence": presence,
            "health": {},
            "stateVersion": self.state_version.model_dump(by_alias=True),
            "uptimeMs": self.uptime_ms,
            "sessionDefaults": {
                "defaultAgentId": "main",
                "mainKey": "main",
                "mainSessionKey": "agent:main:main",
            },
            "authMode": auth_mode,
        }
