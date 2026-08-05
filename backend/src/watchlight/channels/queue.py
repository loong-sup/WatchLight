# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 queue 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Inbound message queue with debounce."""

import asyncio
from collections import defaultdict
from collections.abc import Callable
from typing import Any


class MessageQueue:
    def __init__(self, debounce_ms: int = 500) -> None:
        self.debounce_ms = debounce_ms
        self._queues: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._timers: dict[str, asyncio.Task[None]] = {}

    def enqueue(
        self, session_key: str, message: dict[str, Any], handler: Callable[..., Any]
    ) -> None:
        self._queues[session_key].append(message)

        if session_key in self._timers:
            self._timers[session_key].cancel()

        async def _flush() -> None:
            await asyncio.sleep(self.debounce_ms / 1000)
            messages = self._queues.pop(session_key, [])
            self._timers.pop(session_key, None)
            if messages:
                await handler(session_key, messages)

        self._timers[session_key] = asyncio.create_task(_flush())
