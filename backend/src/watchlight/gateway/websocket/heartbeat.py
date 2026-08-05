# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 heartbeat 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tick heartbeat emitter."""

import asyncio
import time
from typing import Any

from watchlight.gateway.websocket.frames import make_event


class TickEmitter:
    """Periodically sends tick events to a client."""

    def __init__(self, interval_ms: int = 30000) -> None:
        self.interval_ms = interval_ms
        self._task: asyncio.Task[None] | None = None

    async def _loop(self, send_fn: Any) -> None:
        try:
            while True:
                await asyncio.sleep(self.interval_ms / 1000)
                tick = make_event("tick", {"ts": int(time.time() * 1000)})
                await send_fn(tick)
        except asyncio.CancelledError:
            pass

    def start(self, send_fn: Any) -> None:
        self._task = asyncio.create_task(self._loop(send_fn))

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
