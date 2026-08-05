# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 connection 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""WebSocket connection state tracking."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from starlette.websockets import WebSocket


# generated: 09C5e 08X85
@dataclass
class GatewayWsClient:
    ws: WebSocket
    conn_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    client_info: dict[str, Any] = field(default_factory=dict)
    authenticated: bool = False
    subscriptions: set[str] = field(default_factory=set)

    async def send_json(self, data: dict[str, Any]) -> None:
        await self.ws.send_json(data)
