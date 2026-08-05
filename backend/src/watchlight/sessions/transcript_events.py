# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 transcript events 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Transcript event broadcasting — notify UI/listeners on message append."""

from collections.abc import Awaitable, Callable
from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("sessions.transcript_events")

TranscriptListener = Callable[[str, str, dict[str, Any]], Awaitable[None] | None]

_listeners: list[TranscriptListener] = []


def on_transcript_update(listener: TranscriptListener) -> None:
    """Register a listener for transcript updates."""
    _listeners.append(listener)


async def emit_transcript_update(
    session_key: str,
    phase: str,  # "user" | "assistant" | "tool" | "system"
    data: dict[str, Any] | None = None,
) -> None:
    """Emit transcript update event to all listeners."""
    for listener in _listeners:
        try:
            result = listener(session_key, phase, data or {})
            if result is not None:
                await result
        except Exception as e:
            log.error("transcript_listener_error", error=str(e))
