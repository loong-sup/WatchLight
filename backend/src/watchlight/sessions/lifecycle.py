# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 lifecycle 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session lifecycle — complete state machine + event emission."""

import time
from collections.abc import Callable
from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("sessions.lifecycle")

# Valid status transitions
VALID_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"running"},
    "running": {"done", "failed", "killed", "timeout"},
    "done": {"running"},  # Can restart
    "failed": {"running"},  # Can retry
    "killed": {"running"},  # Can restart
    "timeout": {"running"},  # Can retry
}

_listeners: list[Callable[[str, str, dict[str, Any]], None]] = []


def on_session_event(callback: Callable[[str, str, dict[str, Any]], None]) -> None:
    _listeners.append(callback)


def emit_session_event(event: str, session_key: str, data: dict[str, Any] | None = None) -> None:
    for listener in _listeners:
        try:
            listener(event, session_key, data or {})
        except Exception as e:
            log.error("session_event_listener_error", event=event, error=str(e))


def transition_status(current: str | None, target: str) -> bool:
    """Check if a status transition is valid."""
    allowed = VALID_TRANSITIONS.get(current, set())
    return target in allowed


def start_run(session_key: str, entry_patch: dict[str, Any]) -> dict[str, Any]:
    """Mark session as running. Returns patch to apply."""
    now = int(time.time() * 1000)
    patch: dict[str, Any] = {"status": "running"}
    if "startedAt" not in entry_patch:
        patch["startedAt"] = now
    emit_session_event("session.run.started", session_key, {"startedAt": now})
    return patch


def end_run(
    session_key: str,
    status: str = "done",
    input_tokens: int = 0,
    output_tokens: int = 0,
    model: str | None = None,
    model_provider: str | None = None,
    channel: str | None = None,
    runtime_ms: int = 0,
) -> dict[str, Any]:
    """Mark session as done/failed/killed/timeout. Returns patch to apply."""
    now = int(time.time() * 1000)
    patch: dict[str, Any] = {
        "status": status,
        "endedAt": now,
    }
    if input_tokens:
        patch["inputTokens"] = input_tokens
    if output_tokens:
        patch["outputTokens"] = output_tokens
    if input_tokens or output_tokens:
        patch["totalTokens"] = input_tokens + output_tokens
    if model:
        patch["model"] = model
    if model_provider:
        patch["modelProvider"] = model_provider
    if channel:
        patch["lastChannel"] = channel
    if runtime_ms:
        patch["runtimeMs"] = runtime_ms

    emit_session_event(
        "session.run.ended",
        session_key,
        {
            "status": status,
            "tokens": input_tokens + output_tokens,
        },
    )
    return patch
